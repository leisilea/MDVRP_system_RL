"""
RL4CO CVRP 训练脚本
支持容量和距离约束的 CVRP 问题
"""

import torch
import os
from rl4co.envs.routing import MTVRPEnv, MTVRPGenerator
from rl4co.models import AttentionModelPolicy, POMO
from rl4co.utils import RL4COTrainer


def train_cvrp_model(
    num_loc=50,
    capacity=80,
    distance_limit=500,
    num_epochs=100,
    batch_size=512,
    learning_rate=1e-4,
    train_data_size=100000,
    val_data_size=10000,
    output_dir="checkpoints",
):
    """
    训练 CVRP 模型
    
    Args:
        num_loc: 客户数量
        capacity: 车辆容量
        distance_limit: 最大距离限制
        num_epochs: 训练轮数
        batch_size: 批次大小
        learning_rate: 学习率
        train_data_size: 训练数据量（每个epoch）
        val_data_size: 验证数据量
        output_dir: 模型保存目录
    """
    print("="*60)
    print("RL4CO CVRP 模型训练")
    print("="*60)
    print(f"配置:")
    print(f"  客户数: {num_loc}")
    print(f"  容量: {capacity}")
    print(f"  距离限制: {distance_limit}")
    print(f"  训练轮数: {num_epochs}")
    print(f"  批次大小: {batch_size}")
    print(f"  训练数据量: {train_data_size}/epoch")
    print(f"  验证数据量: {val_data_size}")
    print("="*60)
    
    # 创建环境
    generator = MTVRPGenerator(
        num_loc=num_loc,
        variant_preset="vrpl",  # 容量 + 距离限制
        capacity=capacity,
        distance_limit=distance_limit,
        min_demand=1,
        max_demand=10,
        subsample=False,  # 关键：使用 variant_preset 时必须设为 False
    )
    
    env = MTVRPEnv(generator=generator)
    
    # 创建策略网络
    policy = AttentionModelPolicy(
        env_name=env.name,
        num_encoder_layers=6,
        embed_dim=128,
        num_heads=8,
        normalization="instance",
        feedforward_hidden=512,
    )
    
    # 创建 POMO 模型
    model = POMO(
        env=env,
        policy=policy,
        batch_size=batch_size,
        train_data_size=train_data_size,
        val_data_size=val_data_size,
        test_data_size=val_data_size,
        optimizer_kwargs={"lr": learning_rate},
        lr_scheduler="CosineAnnealingLR",
        lr_scheduler_kwargs={"T_max": num_epochs},
    )
    
    # 创建训练器
    os.makedirs(output_dir, exist_ok=True)
    
    trainer = RL4COTrainer(
        max_epochs=num_epochs,
        accelerator="auto",  # 自动选择 GPU 或 CPU
        devices=1,
        precision="16-mixed" if torch.cuda.is_available() else "32",
        gradient_clip_val=1.0,
        default_root_dir=output_dir,
        callbacks=[
            # 保存最佳模型
            {
                "class_path": "lightning.pytorch.callbacks.ModelCheckpoint",
                "init_args": {
                    "monitor": "val/reward",
                    "mode": "max",
                    "save_top_k": 3,
                    "filename": "cvrp-{epoch:02d}-{val_reward:.2f}",
                }
            },
            # 早停
            {
                "class_path": "lightning.pytorch.callbacks.EarlyStopping",
                "init_args": {
                    "monitor": "val/reward",
                    "patience": 20,
                    "mode": "max",
                }
            },
        ],
    )
    
    # 开始训练
    print("\n开始训练...")
    trainer.fit(model)
    
    # 测试
    print("\n开始测试...")
    trainer.test(model)
    
    # 保存最终模型
    final_model_path = os.path.join(output_dir, "final_model.ckpt")
    trainer.save_checkpoint(final_model_path)
    print(f"\n模型已保存到: {final_model_path}")
    
    return model, trainer


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="训练 RL4CO CVRP 模型")
    parser.add_argument("--num_loc", type=int, default=50, help="客户数量")
    parser.add_argument("--capacity", type=float, default=80, help="车辆容量")
    parser.add_argument("--distance_limit", type=float, default=500, help="最大距离")
    parser.add_argument("--epochs", type=int, default=100, help="训练轮数")
    parser.add_argument("--batch_size", type=int, default=512, help="批次大小")
    parser.add_argument("--lr", type=float, default=1e-4, help="学习率")
    parser.add_argument("--output_dir", type=str, default="checkpoints", help="输出目录")
    
    args = parser.parse_args()
    
    model, trainer = train_cvrp_model(
        num_loc=args.num_loc,
        capacity=args.capacity,
        distance_limit=args.distance_limit,
        num_epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        output_dir=args.output_dir,
    )
