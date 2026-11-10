package com.airport.ai.auth;

import com.airport.ai.auth.dto.LoginResponse;
import com.airport.ai.common.CredentialMasker;
import com.airport.ai.common.PageResult;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/**
 * 对应 SRS_NF001 / DEF-S3-010：敏感凭据脱敏传输与存储隔离，
 * 对外序列化与视图响应严禁包含 passwordHash、密码明文或未经脱敏的敏感凭据。
 */
class UserSerializationTest {

    private final ObjectMapper objectMapper = new ObjectMapper().findAndRegisterModules();

    @Test
    void passwordHashNotSerializedButStillAccessibleInternally() throws Exception {
        User u = new User();
        u.setUsername("alice");
        u.setPasswordHash("$2a$10$secret-hash-value");

        String json = objectMapper.writeValueAsString(u);

        assertFalse(json.contains("passwordHash"));
        assertFalse(json.contains("secret-hash-value"));
        assertTrue(json.contains("alice"));
        assertEquals("$2a$10$secret-hash-value", u.getPasswordHash());
    }

    @Test
    void userToStringDoesNotExposePasswordHash() {
        User u = new User();
        u.setId(10L);
        u.setUsername("security_officer");
        u.setRole("OPERATOR");
        u.setStatus("ACTIVE");
        u.setPasswordHash("$2a$10$super-confidential-hash");

        String str = u.toString();
        assertFalse(str.contains("passwordHash"));
        assertFalse(str.contains("super-confidential-hash"));
        assertTrue(str.contains("security_officer"));
    }

    @Test
    void loginResponseDoesNotContainPasswordOrHash() throws Exception {
        LoginResponse.UserView userView = new LoginResponse.UserView(1L, "admin", "Administrator", "SYSTEM_ADMIN");
        LoginResponse resp = new LoginResponse("mock-token-xyz", 1800, userView);

        String json = objectMapper.writeValueAsString(resp);
        assertFalse(json.toLowerCase().contains("password"));
        assertFalse(json.toLowerCase().contains("hash"));
        assertTrue(json.contains("admin"));
        assertTrue(json.contains("mock-token-xyz"));
    }

    @Test
    void userListPageDoesNotExposePasswordHash() throws Exception {
        User u1 = new User();
        u1.setUsername("user1");
        u1.setPasswordHash("$2a$10$hash1");

        User u2 = new User();
        u2.setUsername("user2");
        u2.setPasswordHash("$2a$10$hash2");

        PageResult<User> page = new PageResult<>(List.of(u1, u2), 2L, 1, 10);
        String json = objectMapper.writeValueAsString(page);

        assertFalse(json.contains("passwordHash"));
        assertFalse(json.contains("hash1"));
        assertFalse(json.contains("hash2"));
        assertTrue(json.contains("user1"));
        assertTrue(json.contains("user2"));
    }

    @Test
    void credentialMaskerMasksAllSensitiveKeysRecursively() {
        Map<String, Object> detail = new LinkedHashMap<>();
        detail.put("username", "testuser");
        detail.put("password", "PlainPassword123!");
        detail.put("passwordHash", "$2a$10$e8w8j930dk2ls02ld");
        detail.put("accessToken", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz");
        detail.put("deviceToken", "dev-secret-token-abcdef");
        detail.put("secretKey", "sk_live_1234567890abcdef");
        detail.put("passwordChanged", true);

        Map<String, Object> nested = new LinkedHashMap<>();
        nested.put("accessCredentialRef", "device-cred-9988");
        nested.put("apiKey", "api-key-very-secret");
        detail.put("subConfig", nested);

        Map<String, Object> listItem = new LinkedHashMap<>();
        listItem.put("secret", "topsecret");
        detail.put("tokensList", List.of(listItem));

        CredentialMasker.maskSensitiveFields(detail);

        // 校验敏感字段值全部被掩码
        assertFalse(((String) detail.get("password")).contains("PlainPassword"));
        assertTrue(((String) detail.get("password")).contains("****"));

        assertFalse(((String) detail.get("passwordHash")).contains("e8w8j930"));
        assertTrue(((String) detail.get("passwordHash")).contains("****"));

        assertFalse(((String) detail.get("accessToken")).contains("eyJhbGci"));
        assertFalse(((String) detail.get("deviceToken")).contains("abcdef"));
        assertFalse(((String) detail.get("secretKey")).contains("1234567890"));

        // 布尔值不受掩码影响
        assertEquals(Boolean.TRUE, detail.get("passwordChanged"));

        // 嵌套 Map 脱敏校验
        assertFalse(((String) nested.get("accessCredentialRef")).contains("9988"));
        assertFalse(((String) nested.get("apiKey")).contains("very-secret"));

        // 嵌套 List<Map> 脱敏校验
        assertFalse(((String) listItem.get("secret")).contains("topsecret"));
        assertTrue(((String) listItem.get("secret")).contains("****"));
    }
}
