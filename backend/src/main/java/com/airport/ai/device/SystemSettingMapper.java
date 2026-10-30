package com.airport.ai.device;

import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

@Mapper
public interface SystemSettingMapper {
    @Select("SELECT setting_value FROM system_settings WHERE setting_key = #{key}")
    String findValue(@Param("key") String key);

    @Insert("INSERT INTO system_settings (setting_key, setting_value, updated_by, updated_at) "
            + "VALUES (#{key}, #{value}, #{operator}, CURRENT_TIMESTAMP) "
            + "ON CONFLICT (setting_key) DO UPDATE SET setting_value = EXCLUDED.setting_value, "
            + "updated_by = EXCLUDED.updated_by, updated_at = CURRENT_TIMESTAMP")
    int upsert(@Param("key") String key, @Param("value") String value, @Param("operator") String operator);
}
