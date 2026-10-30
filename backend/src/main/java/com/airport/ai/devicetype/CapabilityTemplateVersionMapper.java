package com.airport.ai.devicetype;

import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;
import java.util.Map;

@Mapper
public interface CapabilityTemplateVersionMapper {
    @Insert("INSERT INTO capability_template_versions (template_id, template_version, template_name, input_params, "
            + "output_params, template_description, changed_by) VALUES (#{templateId}, #{version}, #{name}, "
            + "#{inputParams}::json, #{outputParams}::json, #{description}, #{changedBy}) "
            + "ON CONFLICT (template_id, template_version) DO NOTHING")
    int insert(@Param("templateId") Long templateId, @Param("version") String version, @Param("name") String name,
               @Param("inputParams") String inputParams, @Param("outputParams") String outputParams,
               @Param("description") String description, @Param("changedBy") String changedBy);

    @Select("SELECT template_version AS \"templateVersion\", template_name AS \"templateName\", "
            + "input_params::text AS \"inputParams\", output_params::text AS \"outputParams\", "
            + "template_description AS \"templateDescription\", changed_by AS \"changedBy\", "
            + "created_at AS \"createdAt\" FROM capability_template_versions "
            + "WHERE template_id = #{templateId} ORDER BY id DESC")
    List<Map<String, Object>> findByTemplateId(@Param("templateId") Long templateId);
}
