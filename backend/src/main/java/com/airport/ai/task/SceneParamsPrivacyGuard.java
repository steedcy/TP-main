package com.airport.ai.task;

import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;

import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * 场景参数不得携带旅客真实身份信息（SRS_F010 业务规则6、NF003，DEF-S3-032）。
 * 提交时命中身份类字段名即拒绝建任务，不持久化、不送模型；键名忽略大小写与下划线/连字符。
 */
public final class SceneParamsPrivacyGuard {
    private static final Set<String> IDENTITY_KEYS = Set.of(
            "passengername", "identitydocumentnumber", "identitydocument", "identitynumber", "idnumber",
            "idcard", "idcardnumber", "idno", "documentnumber", "passportnumber", "passportno", "passport",
            "phone", "phonenumber", "mobile", "mobilenumber", "telephone", "email", "realname", "fullname");

    private SceneParamsPrivacyGuard() {}

    public static void reject(Map<String, Object> sceneParams) {
        if (sceneParams == null) return;
        List<String> hits = sceneParams.keySet().stream()
                .filter(k -> k != null && IDENTITY_KEYS.contains(k.replaceAll("[_\\-\\s]", "").toLowerCase()))
                .sorted().toList();
        if (!hits.isEmpty()) {
            throw new BusinessException(ErrorCode.PARAM_FORMAT_ERROR,
                    "场景参数不得包含旅客身份信息字段: " + String.join("、", hits));
        }
    }
}
