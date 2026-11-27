package com.airport.ai.task;

import org.apache.ibatis.annotations.Delete;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

@Mapper
public interface TerminalMapMapper {

    @Select("SELECT id, poi_code AS \"poiCode\", poi_name AS \"poiName\", category, " +
            "pos_x AS \"x\", pos_y AS \"y\", zone_name AS \"zone\", linked_device_code AS \"linkedDeviceCode\", " +
            "bounds_json AS \"boundsJson\" " +
            "FROM terminal_pois ORDER BY category ASC, id ASC")
    List<Map<String, Object>> findAllPois();

    @Select("SELECT id, poi_code AS \"poiCode\" FROM terminal_pois WHERE id = #{id}")
    Map<String, Object> findPoiById(@Param("id") Long id);

    @Insert("INSERT INTO terminal_pois (poi_code, poi_name, category, pos_x, pos_y, zone_name, linked_device_code, created_by) " +
            "VALUES (#{poiCode}, #{poiName}, #{category}, #{x}, #{y}, #{zone}, #{linkedDeviceCode}, #{createdBy})")
    int insertPoi(@Param("poiCode") String poiCode,
                  @Param("poiName") String poiName,
                  @Param("category") String category,
                  @Param("x") BigDecimal x,
                  @Param("y") BigDecimal y,
                  @Param("zone") String zone,
                  @Param("linkedDeviceCode") String linkedDeviceCode,
                  @Param("createdBy") String createdBy);

    @Update("UPDATE terminal_pois SET poi_name = #{poiName}, category = #{category}, pos_x = #{x}, pos_y = #{y}, " +
            "zone_name = #{zone}, linked_device_code = #{linkedDeviceCode}, updated_at = CURRENT_TIMESTAMP WHERE id = #{id}")
    int updatePoi(@Param("id") Long id,
                  @Param("poiName") String poiName,
                  @Param("category") String category,
                  @Param("x") BigDecimal x,
                  @Param("y") BigDecimal y,
                  @Param("zone") String zone,
                  @Param("linkedDeviceCode") String linkedDeviceCode);

    @Update("UPDATE terminal_pois SET pos_x = #{x}, pos_y = #{y}, updated_at = CURRENT_TIMESTAMP " +
            "WHERE linked_device_code = #{deviceCode}")
    int syncPoiByDeviceCode(@Param("deviceCode") String deviceCode,
                            @Param("x") BigDecimal x,
                            @Param("y") BigDecimal y);

    @Delete("DELETE FROM terminal_pois WHERE id = #{id}")
    int deletePoi(@Param("id") Long id);

    @Select("SELECT id, region_code AS \"regionCode\", region_name AS \"regionName\", " +
            "region_type AS \"regionType\", geometry_json AS \"geometryJson\" " +
            "FROM terminal_map_regions ORDER BY id ASC")
    List<Map<String, Object>> findAllRegions();

    @Insert("INSERT INTO terminal_map_regions (region_code, region_name, region_type, geometry_json, created_by) " +
            "VALUES (#{regionCode}, #{regionName}, #{regionType}, #{geometryJson}, #{createdBy})")
    int insertRegion(@Param("regionCode") String regionCode,
                     @Param("regionName") String regionName,
                     @Param("regionType") String regionType,
                     @Param("geometryJson") String geometryJson,
                     @Param("createdBy") String createdBy);

    @Update("UPDATE terminal_map_regions SET region_name = #{regionName}, region_type = #{regionType}, " +
            "geometry_json = #{geometryJson}, updated_at = CURRENT_TIMESTAMP WHERE id = #{id}")
    int updateRegion(@Param("id") Long id,
                     @Param("regionName") String regionName,
                     @Param("regionType") String regionType,
                     @Param("geometryJson") String geometryJson);

    @Delete("DELETE FROM terminal_map_regions WHERE id = #{id}")
    int deleteRegion(@Param("id") Long id);

    @Select("SELECT device_code AS \"deviceCode\", device_name AS \"deviceName\", " +
            "position_x AS \"x\", position_y AS \"y\", area_code AS \"zone\" " +
            "FROM devices WHERE simulated_device_type = 'BAGGAGE_SCANNER' " +
            "AND position_x IS NOT NULL AND position_y IS NOT NULL ORDER BY id ASC")
    List<Map<String, Object>> findBaggageScanners();
}
