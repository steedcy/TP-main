import com.airport.ai.device.DeviceCapabilityMapper;
import com.airport.ai.task.PlanValidationService;
import com.airport.ai.task.PlanValidationResult;
import com.airport.ai.taskdef.TaskDefinition;
import com.airport.ai.taskdef.TaskDefinitionMapper;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;
import java.lang.reflect.Proxy;
import java.nio.file.*;
import java.util.*;

/** Independent packaged-class probe. No product changes, DB, Redis, model or device. */
public class F022V176ContainerProbe {
    static String currentConstraint;
    static Object proxy(Class<?> type) {
        return Proxy.newProxyInstance(type.getClassLoader(), new Class<?>[]{type}, (p, method, args) -> {
            if (method.getName().equals("toString")) return "GPT synthetic mapper";
            if (method.getName().equals("hashCode")) return System.identityHashCode(p);
            if (method.getName().equals("equals")) return p == args[0];
            if (method.getName().equals("findByDefinitionCode")) {
                TaskDefinition def = new TaskDefinition();
                def.setDefinitionCode("EXT_GPT_F176");
                def.setConstraintDescription(currentConstraint);
                return Optional.of(def);
            }
            if (method.getReturnType() == boolean.class) return true;
            if (method.getReturnType() == int.class) return 0;
            return null;
        });
    }
    public static void main(String[] args) throws Exception {
        var output = new LinkedHashMap<String,Object>();
        output.put("layer", "isolated Spring registration + direct seven-argument service; mapper fixtures only, not live HTTP acceptance");
        var constructors = new ArrayList<Object>();
        for (var c : PlanValidationService.class.getDeclaredConstructors()) {
            constructors.add(Map.of("parameterCount", c.getParameterCount(), "constructorAnnotations", Arrays.toString(c.getAnnotations()), "parameterAnnotations", Arrays.deepToString(c.getParameterAnnotations())));
        }
        output.put("constructors", constructors);
        var capabilities = (DeviceCapabilityMapper)proxy(DeviceCapabilityMapper.class);
        var definitions = (TaskDefinitionMapper)proxy(TaskDefinitionMapper.class);
        try (var ctx = new AnnotationConfigApplicationContext()) {
            ctx.registerBean(DeviceCapabilityMapper.class, () -> capabilities);
            ctx.registerBean(TaskDefinitionMapper.class, () -> definitions);
            ctx.register(PlanValidationService.class);
            try {
                ctx.refresh();
                output.put("container", Map.of("started", true));
            } catch (Throwable failure) {
                var chain = new ArrayList<String>();
                for (Throwable t=failure; t!=null; t=t.getCause()) chain.add(t.getClass().getName()+": "+t.getMessage());
                output.put("container", Map.of("started", false, "failureChain", chain));
            }
        }
        var service = new PlanValidationService(capabilities, definitions);
        var observations = new ArrayList<Object>();
        String[][] cases = {
            {"original-prohibition", "禁止前往F2_TEST_GATE；仅允许前往F2_ZONE_A。", "F2_TEST_GATE", "FAIL"},
            {"original-allowed-control", "仅允许前往F2_TEST_GATE。", "F2_TEST_GATE", "PASS"},
            {"allowed-zone-control", "禁止前往F2_TEST_GATE；仅允许前往F2_ZONE_A。", "F2_ZONE_A", "PASS"},
            {"other-zone-rejected", "仅允许前往F2_ZONE_A。", "F2_ZONE_B", "FAIL"}
        };
        for (String[] test : cases) {
            currentConstraint = test[1];
            var step = new LinkedHashMap<String,Object>();
            step.put("stepSeq",1); step.put("stepGoal","Synthetic passenger guidance");
            step.put("capabilityType","CAP_NAVIGATION"); step.put("inputParams",Map.of("targetLocation",test[2]));
            step.put("precondition","device online");step.put("completionCondition","routeGenerated=true");
            step.put("failureHandling","manual handling");step.put("stepTimeout",600);
            var agent = Map.<String,Object>of("onlineStatus","ONLINE","workStatus","IDLE","capabilities",List.of("CAP_NAVIGATION"));
            PlanValidationResult actual = service.validate(List.of(step), List.of(agent), List.of("CAP_NAVIGATION"), "EXT_GPT_F176", 0, 176L, "routeGenerated=true");
            observations.add(Map.of("name",test[0],"constraint",test[1],"target",test[2],"expectedConstraintResult",test[3],"actualConstraintResult",actual.getConstraintCheckResult(),"allPassed",actual.isAllPassed(),"errors",actual.getErrors(),"result",test[3].equals(actual.getConstraintCheckResult()) ? "P" : "F"));
        }
        output.put("componentObservations", observations);
        Files.writeString(Path.of(args[0]), new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(output));
        System.out.println("Captured isolated Spring constructor result and four service observations; no live-business P claimed.");
    }
}
