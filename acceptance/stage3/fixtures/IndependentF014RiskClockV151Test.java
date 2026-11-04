package com.airport.ai.risk;

import com.airport.ai.task.PlanVersion;
import com.airport.ai.common.BusinessException;
import com.airport.ai.common.ErrorCode;
import org.junit.jupiter.api.Test;
import org.mockito.MockedStatic;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import static org.mockito.Mockito.*;
import static org.junit.jupiter.api.Assertions.*;

/** Independent exact clock assertions. Real RiskAssessmentService; only mapper/clock are controlled. */
public class IndependentF014RiskClockV151Test {
    RiskRuleMapper mapper=mock(RiskRuleMapper.class);
    RiskAssessmentService service=new RiskAssessmentService(mapper,0.8,60,1);
    PlanVersion plan(String confidence,String capability) {
        PlanVersion p=new PlanVersion();
        p.setStructureCheckResult("PASS");p.setCapabilityCheckResult("PASS");p.setConstraintCheckResult("PASS");
        p.setPlanSteps("[{\"stepSeq\":1,\"capabilityType\":\""+capability+"\",\"inputParams\":{\"targetLocation\":\"F2_TEST_GATE\"}}]");
        p.setConfidence(new BigDecimal(confidence));return p;
    }
    @Test void exactSixtySecondsAndConfidenceGridAndAllSignalSets() {
        LocalDateTime now=LocalDateTime.of(2026,11,4,12,0,0);
        PlanVersion low=plan("0.799999","CAP_NAVIGATION"), boundary=plan("0.800000","CAP_NAVIGATION"), above=plan("0.800001","CAP_NAVIGATION");
        when(mapper.findByEnabled(true)).thenReturn(List.of());when(mapper.findAll()).thenReturn(List.of());
        try(MockedStatic<LocalDateTime> clock=mockStatic(LocalDateTime.class,CALLS_REAL_METHODS)) {
            clock.when(LocalDateTime::now).thenReturn(now);
            assertEquals("LOW",service.assess(low,"GENERAL_GUIDANCE",now.minusSeconds(60),false,3).getRiskLevel(),"exact 60s is not stale");
            assertEquals("LOW",service.assess(low,"GENERAL_GUIDANCE",now.minusSeconds(60).plusNanos(1),false,3).getRiskLevel());
            assertEquals("HIGH",service.assess(low,"GENERAL_GUIDANCE",now.minusSeconds(60).minusNanos(1),false,3).getRiskLevel(),"60s + 1ns is stale");
            assertEquals("LOW",service.assess(boundary,"GENERAL_GUIDANCE",now,true,3).getRiskLevel(),"exact .8 not low");
            assertEquals("LOW",service.assess(above,"GENERAL_GUIDANCE",now,true,3).getRiskLevel());
            assertEquals("HIGH",service.assess(low,"GENERAL_GUIDANCE",now,true,3).getRiskLevel());
            for(int mask=0;mask<8;mask++) {
                boolean lc=(mask&1)!=0, diverse=(mask&2)!=0, stale=(mask&4)!=0;
                RiskAssessmentResult result=service.assess(lc?low:above,"GENERAL_GUIDANCE",stale?now.minusSeconds(61):now,diverse,3);
                int count=Integer.bitCount(mask);
                assertEquals(count>=2?"HIGH":"LOW",result.getRiskLevel(),"mask="+mask);
                assertEquals(count>=2?"BASELINE_DOWNGRADE":"AUTO_EXECUTE",result.getRecommendedAction());
                assertEquals(count>=2?"RISK_SIGNAL_COMBINATION":null,result.getRiskReasonCode());
                String basis=result.getJudgmentBasis(),timeline=result.timelineDetail("independent clock");
                assertEquals(lc,basis.contains("模型低置信度"));assertEquals(diverse,basis.contains("候选差异较大"));assertEquals(stale,basis.contains("上下文快照接近过期"));
                assertTrue(timeline.contains(basis));assertTrue(timeline.contains("规则集版本=V1.0"));
            }
        }
    }
    @Test void eachFailedOrMissingHardCheckRejectsAtConfidenceOne() {
        for(int field=0;field<3;field++) for(String result:new String[]{"FAIL",null}) {
            PlanVersion p=plan("1.0","CAP_NAVIGATION");
            if(field==0)p.setStructureCheckResult(result);if(field==1)p.setCapabilityCheckResult(result);if(field==2)p.setConstraintCheckResult(result);
            BusinessException e=assertThrows(BusinessException.class,()->service.assess(p,"GENERAL_GUIDANCE",null,false,3));
            assertEquals(ErrorCode.SUPERVISION_ON_UNVALIDATED_PLAN,e.getErrorCode());
        }
        verifyNoInteractions(mapper);
    }
    @Test void navigationAndEscortSpecialRuleHavePriorityOverAllSignals() {
        RiskRule r=new RiskRule();r.setRuleCode("RULE_ESCORT_SPECIAL_PASSENGER");
        when(mapper.findByEnabled(true)).thenReturn(List.of(r));when(mapper.findAll()).thenReturn(List.of(r));
        for(String cap:List.of("CAP_NAVIGATION","CAP_ESCORT")) {
            PlanVersion p=plan("0.2",cap);
            RiskAssessmentResult result=service.assess(p,"SPECIAL_PASSENGER_SERVICE",LocalDateTime.now().minusSeconds(70),true,3);
            assertEquals("RULE_ESCORT_SPECIAL_PASSENGER",result.getRiskReasonCode());assertEquals("HIGH",result.getRiskLevel());
            assertTrue(result.getJudgmentBasis().contains(cap));assertTrue(result.getJudgmentBasis().contains("绑定移动服务机器人"));
            assertEquals("RISK_SIGNAL_COMBINATION",service.assess(p,"GENERAL_GUIDANCE",LocalDateTime.now().minusSeconds(70),true,3).getRiskReasonCode());
            assertEquals("LOW",service.assess(plan("0.99",cap),"GENERAL_GUIDANCE",LocalDateTime.now(),false,3).getRiskLevel());
        }
    }
}
