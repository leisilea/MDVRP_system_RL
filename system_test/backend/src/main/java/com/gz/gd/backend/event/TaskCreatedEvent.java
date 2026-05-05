package com.gz.gd.backend.event;

/**
 * 任务创建事件
 * 用于在事务提交后触发异步任务执行
 */
public class TaskCreatedEvent {
    private final Long taskId;
    
    public TaskCreatedEvent(Long taskId) {
        this.taskId = taskId;
    }
    
    public Long getTaskId() {
        return taskId;
    }
}
