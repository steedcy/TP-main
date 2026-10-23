package com.airport.ai.auth;

import org.apache.ibatis.annotations.Mapper;

import java.util.List;
import java.util.Optional;

/** 分页查询（findByStatusPaged/findAllPaged）配合PageHelper.startPage()使用，见UserService */
@Mapper
public interface UserMapper {
    Optional<User> findById(Long id);
    Optional<User> findByUsername(String username);
    boolean existsByUsername(String username);
    List<User> findByStatusPaged(String status);
    List<User> findAllPaged();
    int insert(User user);
    int update(User user);
}
