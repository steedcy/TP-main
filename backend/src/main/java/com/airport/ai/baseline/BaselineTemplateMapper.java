package com.airport.ai.baseline;

import org.apache.ibatis.annotations.Mapper;

import java.util.List;
import java.util.Optional;

@Mapper
public interface BaselineTemplateMapper {
    Optional<BaselineTemplate> findById(Long id);
    List<BaselineTemplate> findAll();
    boolean existsByTemplateName(String templateName);

    /** 匹配优先级：任务族精确匹配 > 步骤数少优先 > 最近试运行通过优先（对应5.4.6），由Service层二次排序 */
    List<BaselineTemplate> findByTaskFamilyAndTemplateStatus(String taskFamily, String templateStatus);

    int insert(BaselineTemplate template);
    int update(BaselineTemplate template);
    int deleteById(Long id);
}
