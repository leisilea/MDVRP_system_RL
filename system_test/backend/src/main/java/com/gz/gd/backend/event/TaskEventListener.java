package com.gz.gd.backend.event;

import com.gz.gd.backend.service.AsyncAlgorithmService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import org.springframework.transaction.event.TransactionPhase;
import org.springframework.transaction.event.TransactionalEventListener;

/**
 * 任务事件监听器
 * 监听任务创建事件，在事务提交后执行异步任务
 */
@Slf4j
@Component
public class TaskEventListener {
    
    @Autowired
    private AsyncAlgorithmService asyncAlgorithmService;
    
    /**
     * 处理任务创建事件
     * 在事务提交后执行，确保任务已经保存到数据库
     */
    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    public void handleTaskCreated(TaskCreatedEvent event) {
        log.info("事务已提交，开始执行异步任务 - 任务ID: {}", event.getTaskId());
        asyncAlgorithmService.executeAlgorithmTask(event.getTaskId());
    }
}
