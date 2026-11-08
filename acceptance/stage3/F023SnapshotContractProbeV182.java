import com.airport.ai.situation.SituationController;
import com.airport.ai.common.PageResult;
import com.airport.ai.device.*;
import com.fasterxml.jackson.databind.json.JsonMapper;
import java.math.BigDecimal;
import java.util.*;
import static org.mockito.Mockito.*;
import static org.mockito.ArgumentMatchers.*;

/** Independent service contract fixture; no database/schema constraint changes. */
public class F023SnapshotContractProbeV182 {
 public static void main(String[] args) throws Exception {
  var service=mock(DeviceAgentService.class);
  var caps=mock(DeviceCapabilityMapper.class);
  var controller=new SituationController(service,caps);
  var agents=new ArrayList<DeviceAgent>();
  var coordinates=Arrays.asList(new BigDecimal[]{null,BigDecimal.ONE},new BigDecimal[]{BigDecimal.ONE,null},new BigDecimal[]{null,null},new BigDecimal[]{BigDecimal.ZERO,BigDecimal.ZERO},new BigDecimal[]{new BigDecimal("1260"),new BigDecimal("6895")});
  for(int i=0;i<coordinates.size();i++) {
   var a=new DeviceAgent();a.setId((long)i+1);a.setDeviceId((long)i+1);a.setAgentCode("CONTRACT_"+i);a.setAgentStatus("ENABLED");a.setOnlineStatus("ONLINE");a.setWorkStatus("IDLE");agents.add(a);
   var d=new Device();d.setId((long)i+1);d.setDeviceCode("CONTRACT_"+i);d.setDeviceName("CONTRACT_"+i);d.setDeviceTypeCode("SMART_DISPLAY");d.setPositionX(coordinates.get(i)[0]);d.setPositionY(coordinates.get(i)[1]);when(service.getDeviceOf(a)).thenReturn(d);
  }
  when(service.list(eq("ENABLED"),isNull(),eq(1),eq(100))).thenReturn(new PageResult<>(agents,agents.size(),1,100));
  when(caps.findByDeviceIdAndCapabilityStatus(anyLong(),eq("ENABLED"))).thenReturn(List.of());
  var snapshot=controller.snapshot();var markers=snapshot.getData().agents();
  boolean nullX=markers.get(0).location().x()==null && markers.get(0).location().y().equals(BigDecimal.ONE);
  boolean nullY=markers.get(1).location().y()==null && markers.get(1).location().x().equals(BigDecimal.ONE);
  boolean both=markers.get(2).location().x()==null && markers.get(2).location().y()==null;
  if(!nullX||!nullY||!both||markers.size()!=5)throw new AssertionError("null coordinate contract lost");
  System.out.println(JsonMapper.builder().findAndAddModules().build().writeValueAsString(Map.of("tag","V1.181","productSha","67fb8960245d08c4d74be85e515bbe325ca21b0f","layer","service: real controller, mocked upstream service; no persisted null device","checks",Map.of("nullXKept",nullX,"nullYKept",nullY,"bothNullKept",both,"allFiveRowsRetained",markers.size()==5),"snapshot",snapshot)));
 }
}
