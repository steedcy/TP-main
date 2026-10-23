package com.airport.ai.device;

import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.time.LocalDateTime;
import java.util.Base64;
import java.util.HexFormat;

/** Issues per-device bearer tokens, storing only a lookup hash and encrypted outbound copy. */
@Service
public class DeviceCredentialService {

    private static final int GCM_TAG_BITS = 128;
    private static final int IV_BYTES = 12;
    private final DeviceMapper deviceMapper;
    private final DeviceAgentMapper deviceAgentMapper;
    private final SecureRandom secureRandom = new SecureRandom();
    private final byte[] encryptionKey;

    public DeviceCredentialService(DeviceMapper deviceMapper,
                                   DeviceAgentMapper deviceAgentMapper,
                                   @Value("${app.device.credential-encryption-key:}") String configuredKey) {
        this.deviceMapper = deviceMapper;
        this.deviceAgentMapper = deviceAgentMapper;
        this.encryptionKey = configuredKey == null || configuredKey.isBlank()
                ? null : sha256(configuredKey.getBytes(StandardCharsets.UTF_8));
    }

    @Transactional
    public IssuedToken rotate(String deviceCode) {
        Device device = deviceMapper.findByDeviceCode(deviceCode)
                .orElseThrow(() -> new BusinessException(ErrorCode.DEVICE_NOT_FOUND));
        byte[] random = new byte[32];
        secureRandom.nextBytes(random);
        String token = Base64.getUrlEncoder().withoutPadding().encodeToString(random);
        LocalDateTime issuedAt = LocalDateTime.now();
        deviceMapper.updateDeviceToken(device.getId(), hashToken(token), encrypt(token), issuedAt);
        return new IssuedToken(token, issuedAt);
    }

    public String tokenFor(Device device) {
        if (device.getDeviceTokenCiphertext() == null || device.getDeviceTokenCiphertext().isBlank()) {
            throw new BusinessException(ErrorCode.DEVICE_TOKEN_NOT_CONFIGURED);
        }
        return decrypt(device.getDeviceTokenCiphertext());
    }

    public boolean matchesDeviceCode(String deviceCode, String presentedToken) {
        if (presentedToken == null || presentedToken.isBlank()) return false;
        return deviceMapper.findByDeviceCode(deviceCode)
                .map(device -> matches(device.getDeviceTokenHash(), presentedToken))
                .orElse(false);
    }

    public boolean matchesAgentCode(String agentCode, String presentedToken) {
        if (presentedToken == null || presentedToken.isBlank()) return false;
        return deviceAgentMapper.findByAgentCode(agentCode)
                .flatMap(agent -> deviceMapper.findById(agent.getDeviceId()))
                .map(device -> matches(device.getDeviceTokenHash(), presentedToken))
                .orElse(false);
    }

    private boolean matches(String expectedHash, String token) {
        if (expectedHash == null || expectedHash.isBlank()) return false;
        byte[] expected = expectedHash.getBytes(StandardCharsets.US_ASCII);
        byte[] actual = hashToken(token).getBytes(StandardCharsets.US_ASCII);
        return MessageDigest.isEqual(expected, actual);
    }

    private String hashToken(String token) {
        return HexFormat.of().formatHex(sha256(token.getBytes(StandardCharsets.UTF_8)));
    }

    private String encrypt(String plaintext) {
        byte[] key = requireEncryptionKey();
        try {
            byte[] iv = new byte[IV_BYTES];
            secureRandom.nextBytes(iv);
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.ENCRYPT_MODE, new SecretKeySpec(key, "AES"), new GCMParameterSpec(GCM_TAG_BITS, iv));
            byte[] encrypted = cipher.doFinal(plaintext.getBytes(StandardCharsets.UTF_8));
            byte[] packed = new byte[iv.length + encrypted.length];
            System.arraycopy(iv, 0, packed, 0, iv.length);
            System.arraycopy(encrypted, 0, packed, iv.length, encrypted.length);
            return Base64.getEncoder().encodeToString(packed);
        } catch (Exception ex) {
            throw new IllegalStateException("无法加密设备访问令牌", ex);
        }
    }

    private String decrypt(String encoded) {
        byte[] key = requireEncryptionKey();
        try {
            byte[] packed = Base64.getDecoder().decode(encoded);
            if (packed.length <= IV_BYTES) throw new IllegalArgumentException("Encrypted token is truncated");
            byte[] iv = new byte[IV_BYTES];
            byte[] encrypted = new byte[packed.length - IV_BYTES];
            System.arraycopy(packed, 0, iv, 0, IV_BYTES);
            System.arraycopy(packed, IV_BYTES, encrypted, 0, encrypted.length);
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.DECRYPT_MODE, new SecretKeySpec(key, "AES"), new GCMParameterSpec(GCM_TAG_BITS, iv));
            return new String(cipher.doFinal(encrypted), StandardCharsets.UTF_8);
        } catch (Exception ex) {
            throw new IllegalStateException("无法解密设备访问令牌；请检查 DEVICE_CREDENTIAL_ENCRYPTION_KEY", ex);
        }
    }

    private byte[] requireEncryptionKey() {
        if (encryptionKey == null) {
            throw new BusinessException(ErrorCode.DEVICE_CREDENTIAL_KEY_NOT_CONFIGURED,
                    "请先配置DEVICE_CREDENTIAL_ENCRYPTION_KEY（建议至少32个随机字符）");
        }
        return encryptionKey;
    }

    private static byte[] sha256(byte[] value) {
        try {
            return MessageDigest.getInstance("SHA-256").digest(value);
        } catch (Exception ex) {
            throw new IllegalStateException("SHA-256不可用", ex);
        }
    }

    public record IssuedToken(String token, LocalDateTime issuedAt) {}
}
