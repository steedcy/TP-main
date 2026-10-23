package com.airport.ai.common;

import com.github.pagehelper.PageInfo;

import java.util.List;

/**
 * 统一分页返回结构，字段名对齐迁移前Spring Data Page的JSON形状（content/totalElements/page/size），
 * 前端各列表页（DeviceListView等）已按此形状解析响应，迁移到MyBatis+PageHelper后不改前端代码。
 */
public class PageResult<T> {

    private List<T> content;
    private long totalElements;
    private int page;
    private int size;

    public PageResult(List<T> content, long totalElements, int page, int size) {
        this.content = content;
        this.totalElements = totalElements;
        this.page = page;
        this.size = size;
    }

    public static <T> PageResult<T> of(PageInfo<T> pageInfo) {
        return new PageResult<>(pageInfo.getList(), pageInfo.getTotal(), pageInfo.getPageNum(), pageInfo.getPageSize());
    }

    /** 用于Service层返回类型与Controller层DTO映射类型不一致时，先转换列表内容再重新包装 */
    public <R> PageResult<R> map(java.util.function.Function<T, R> mapper) {
        return new PageResult<>(content.stream().map(mapper).toList(), totalElements, page, size);
    }

    public List<T> getContent() { return content; }
    public long getTotalElements() { return totalElements; }
    public int getPage() { return page; }
    public int getSize() { return size; }
}
