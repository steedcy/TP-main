package com.airport.ai.risk;

import org.apache.ibatis.annotations.Mapper;

import java.util.List;
import java.util.Optional;

@Mapper
public interface RiskRuleMapper {
    List<RiskRule> findAll();
    List<RiskRule> findByEnabled(Boolean enabled);
    Optional<RiskRule> findByRuleCode(String ruleCode);
    boolean existsByRuleCode(String ruleCode);
    int insert(RiskRule rule);
    int update(RiskRule rule);
}
