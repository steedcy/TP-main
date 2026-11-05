package com.airport.ai.task;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
/** SRS F018 default field only. Does not claim a persisted PENDING lifecycle transition. */
public class IndependentF018StateDefaultV166Test {
 @Test void untreatedExceptionDefaultsPendingWithoutInventedRecovery() {
  var exception = new TaskException();
  assertEquals("PENDING", exception.getExceptionStatus());
  assertNull(exception.getRecoveryResult());
  assertNull(exception.getResolvedAt());
 }
}
