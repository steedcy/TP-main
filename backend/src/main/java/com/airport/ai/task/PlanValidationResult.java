package com.airport.ai.task;

import java.util.ArrayList;
import java.util.List;

/**
 * 对应5.4.4计划三类校验结果。三类依次执行，前一类不通过时仍继续收集后续错误用于展示，
 * 但整体判定为不通过（业务规则5）；全部通过后方可冻结版本（业务规则8）。
 */
public class PlanValidationResult {

    public static class ValidationError {
        private final String errorType;
        private final String description;
        private final Integer stepSeq;
        private final String reasonCode;

        public ValidationError(String errorType, String description, Integer stepSeq, String reasonCode) {
            this.errorType = errorType;
            this.description = description;
            this.stepSeq = stepSeq;
            this.reasonCode = reasonCode;
        }

        public String getErrorType() { return errorType; }
        public String getDescription() { return description; }
        public Integer getStepSeq() { return stepSeq; }
        public String getReasonCode() { return reasonCode; }
    }

    private String structureCheckResult = "PASS";
    private String capabilityCheckResult = "PASS";
    private String constraintCheckResult = "PASS";
    private final List<ValidationError> errors = new ArrayList<>();

    public void failStructure(String description, Integer stepSeq, String reasonCode) {
        structureCheckResult = "FAIL";
        errors.add(new ValidationError("STRUCTURE", description, stepSeq, reasonCode));
    }

    public void failCapability(String description, Integer stepSeq, String reasonCode) {
        capabilityCheckResult = "FAIL";
        errors.add(new ValidationError("CAPABILITY", description, stepSeq, reasonCode));
    }

    public void failConstraint(String description, Integer stepSeq, String reasonCode) {
        constraintCheckResult = "FAIL";
        errors.add(new ValidationError("CONSTRAINT", description, stepSeq, reasonCode));
    }

    public boolean isAllPassed() {
        return "PASS".equals(structureCheckResult) && "PASS".equals(capabilityCheckResult)
                && "PASS".equals(constraintCheckResult);
    }

    public String getStructureCheckResult() { return structureCheckResult; }
    public String getCapabilityCheckResult() { return capabilityCheckResult; }
    public String getConstraintCheckResult() { return constraintCheckResult; }
    public List<ValidationError> getErrors() { return errors; }
}
