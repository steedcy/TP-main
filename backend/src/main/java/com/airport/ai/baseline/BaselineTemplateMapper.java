package com.airport.ai.baseline;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Mapper
public interface BaselineTemplateMapper {
    Optional<BaselineTemplate> findById(Long id);
    List<BaselineTemplate> findAll();
    boolean existsByTemplateName(String templateName);

    /** 匹配优先级：任务族精确匹配 > 步骤数少优先 > 最近试运行通过优先（对应5.4.6），由Service层二次排序 */
    List<BaselineTemplate> findByTaskFamilyAndTemplateStatus(String taskFamily, String templateStatus);

    /** 查询指定模板及其版本绑定的最近试运行通过时间（DRY_RUN_SUCCEEDED）（DEF-S3-097） */
    LocalDateTime findLatestDryRunPassedTime(@Param("templateId") Long templateId,
                                             @Param("templateVersion") String templateVersion);

    int insert(BaselineTemplate template);
    int update(BaselineTemplate template);
    int deleteById(Long id);
}
