package com.airport.ai.auth;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/** 对外序列化不得包含passwordHash；POJO内部读写（认证比对、持久化映射）不受影响。 */
class UserSerializationTest {

    @Test
    void passwordHashNotSerializedButStillAccessibleInternally() throws Exception {
        User u = new User();
        u.setUsername("alice");
        u.setPasswordHash("$2a$10$secret-hash-value");

        String json = new ObjectMapper().findAndRegisterModules().writeValueAsString(u);

        assertFalse(json.contains("passwordHash"));
        assertFalse(json.contains("secret-hash-value"));
        assertTrue(json.contains("alice"));
        assertEquals("$2a$10$secret-hash-value", u.getPasswordHash());
    }
}
