"""
遗传算法优化器
用于优化策略阈值和参数
"""
from typing import List, Dict, Any, Callable, Tuple, Optional
from dataclasses import dataclass
import random
import copy
import pandas as pd
import numpy as np

from .strategy_builder import StrategyRule, Condition, Operator
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Gene:
    """基因 - 表示一个阈值参数"""
    factor: str
    threshold: float
    operator: Operator
    weight: float
    
    def mutate(self, mutation_rate: float = 0.1, mutation_range: float = 0.1):
        """基因变异"""
        if random.random() < mutation_rate:
            # 阈值变异
            self.threshold *= (1 + random.uniform(-mutation_range, mutation_range))
        
        if random.random() < mutation_rate:
            # 权重变异
            self.weight = max(0.1, min(2.0, self.weight + random.uniform(-0.2, 0.2)))


@dataclass
class Individual:
    """个体 - 表示一个完整的策略"""
    genes: List[Gene]
    fitness: float = 0.0
    
    def to_strategy_rule(self, name: str = "GA_Strategy") -> StrategyRule:
        """转换为策略规则"""
        conditions = [
            Condition(
                factor=gene.factor,
                operator=gene.operator,
                threshold=gene.threshold,
                weight=gene.weight
            )
            for gene in self.genes
        ]
        
        return StrategyRule(
            name=name,
            description="遗传算法优化策略",
            conditions=conditions
        )
    
    @classmethod
    def from_strategy_rule(cls, rule: StrategyRule) -> 'Individual':
        """从策略规则创建个体"""
        genes = [
            Gene(
                factor=c.factor,
                threshold=c.threshold,
                operator=c.operator,
                weight=c.weight
            )
            for c in rule.conditions
        ]
        
        return cls(genes=genes)
    
    def mutate(self, mutation_rate: float = 0.1):
        """个体变异"""
        for gene in self.genes:
            gene.mutate(mutation_rate)
    
    def crossover(self, other: 'Individual') -> Tuple['Individual', 'Individual']:
        """交叉操作"""
        if len(self.genes) != len(other.genes):
            return copy.deepcopy(self), copy.deepcopy(other)
        
        # 单点交叉
        crossover_point = random.randint(1, len(self.genes) - 1)
        
        child1_genes = self.genes[:crossover_point] + other.genes[crossover_point:]
        child2_genes = other.genes[:crossover_point] + self.genes[crossover_point:]
        
        child1 = Individual(genes=copy.deepcopy(child1_genes))
        child2 = Individual(genes=copy.deepcopy(child2_genes))
        
        return child1, child2


class GAOptimizer:
    """
    遗传算法优化器
    
    用于优化策略阈值和权重
    """
    
    def __init__(
        self,
        population_size: int = 50,
        generations: int = 100,
        mutation_rate: float = 0.1,
        crossover_rate: float = 0.8,
        elitism: int = 5
    ):
        """
        初始化
        
        Args:
            population_size: 种群大小
            generations: 迭代代数
            mutation_rate: 变异率
            crossover_rate: 交叉率
            elitism: 精英保留数量
        """
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.elitism = elitism
        
        self.population: List[Individual] = []
        self.best_individual: Optional[Individual] = None
        self.fitness_history: List[float] = []
    
    def initialize_population(
        self,
        base_rule: StrategyRule,
        threshold_ranges: Dict[str, Tuple[float, float]] = None
    ):
        """
        初始化种群
        
        Args:
            base_rule: 基础策略规则
            threshold_ranges: 各因子的阈值范围 {factor: (min, max)}
        """
        self.population = []
        
        for i in range(self.population_size):
            individual = Individual.from_strategy_rule(base_rule)
            
            # 随机扰动阈值
            for gene in individual.genes:
                if threshold_ranges and gene.factor in threshold_ranges:
                    min_val, max_val = threshold_ranges[gene.factor]
                    gene.threshold = random.uniform(min_val, max_val)
                else:
                    # 默认在±20%范围内扰动
                    gene.threshold *= random.uniform(0.8, 1.2)
                
                # 随机权重
                gene.weight = random.uniform(0.5, 1.5)
            
            self.population.append(individual)
        
        logger.info(f"初始化种群: {self.population_size}个个体")
    
    def evaluate_fitness(
        self,
        individual: Individual,
        factor_data: pd.DataFrame,
        returns: pd.Series,
        fitness_func: Callable = None
    ) -> float:
        """
        评估适应度
        
        Args:
            individual: 个体
            factor_data: 因子数据
            returns: 收益数据
            fitness_func: 适应度函数
            
        Returns:
            float: 适应度值
        """
        if fitness_func is None:
            fitness_func = self._default_fitness
        
        rule = individual.to_strategy_rule()
        fitness = fitness_func(rule, factor_data, returns)
        
        return fitness
    
    def _default_fitness(
        self,
        rule: StrategyRule,
        factor_data: pd.DataFrame,
        returns: pd.Series
    ) -> float:
        """
        默认适应度函数
        
        基于夏普比率
        """
        # 生成信号
        signals = []
        for idx, row in factor_data.iterrows():
            factor_values = row.to_dict()
            satisfied, score = rule.evaluate(factor_values)
            signals.append(score if satisfied else 0)
        
        signals = pd.Series(signals, index=factor_data.index)
        
        # 计算策略收益
        strategy_returns = returns * (signals > 0).astype(int)
        
        if strategy_returns.std() == 0:
            return 0
        
        # 夏普比率
        sharpe = strategy_returns.mean() / strategy_returns.std() * np.sqrt(252)
        
        # 加上胜率作为辅助指标
        win_rate = (strategy_returns > 0).sum() / (strategy_returns != 0).sum() if (strategy_returns != 0).sum() > 0 else 0
        
        return sharpe + win_rate * 0.5
    
    def select_parent(self) -> Individual:
        """
        选择父代 (锦标赛选择)
        """
        tournament_size = 3
        tournament = random.sample(self.population, min(tournament_size, len(self.population)))
        return max(tournament, key=lambda x: x.fitness)
    
    def evolve(
        self,
        factor_data: pd.DataFrame,
        returns: pd.Series,
        fitness_func: Callable = None,
        verbose: bool = True
    ) -> Individual:
        """
        执行进化
        
        Args:
            factor_data: 因子数据
            returns: 收益数据
            fitness_func: 适应度函数
            verbose: 是否打印进度
            
        Returns:
            Individual: 最优个体
        """
        for generation in range(self.generations):
            # 评估适应度
            for individual in self.population:
                individual.fitness = self.evaluate_fitness(
                    individual, factor_data, returns, fitness_func
                )
            
            # 排序
            self.population.sort(key=lambda x: x.fitness, reverse=True)
            
            # 记录最优
            current_best = self.population[0]
            self.fitness_history.append(current_best.fitness)
            
            if self.best_individual is None or current_best.fitness > self.best_individual.fitness:
                self.best_individual = copy.deepcopy(current_best)
            
            if verbose and generation % 10 == 0:
                logger.info(f"Generation {generation}: Best Fitness = {current_best.fitness:.4f}")
            
            # 创建新一代
            new_population = []
            
            # 精英保留
            new_population.extend(copy.deepcopy(self.population[:self.elitism]))
            
            # 生成新个体
            while len(new_population) < self.population_size:
                # 选择父代
                parent1 = self.select_parent()
                parent2 = self.select_parent()
                
                # 交叉
                if random.random() < self.crossover_rate:
                    child1, child2 = parent1.crossover(parent2)
                else:
                    child1, child2 = copy.deepcopy(parent1), copy.deepcopy(parent2)
                
                # 变异
                child1.mutate(self.mutation_rate)
                child2.mutate(self.mutation_rate)
                
                new_population.extend([child1, child2])
            
            # 截断到种群大小
            self.population = new_population[:self.population_size]
        
        # 最终评估
        for individual in self.population:
            individual.fitness = self.evaluate_fitness(
                individual, factor_data, returns, fitness_func
            )
        
        self.population.sort(key=lambda x: x.fitness, reverse=True)
        
        if self.best_individual is None or self.population[0].fitness > self.best_individual.fitness:
            self.best_individual = copy.deepcopy(self.population[0])
        
        logger.info(f"进化完成: 最优适应度 = {self.best_individual.fitness:.4f}")
        
        return self.best_individual
    
    def get_optimized_strategy(self) -> StrategyRule:
        """获取优化后的策略"""
        if self.best_individual is None:
            raise RuntimeError("尚未进行优化")
        
        return self.best_individual.to_strategy_rule("GA_Optimized")
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """获取优化报告"""
        if not self.fitness_history:
            return {}
        
        return {
            'generations': len(self.fitness_history),
            'initial_fitness': self.fitness_history[0],
            'final_fitness': self.fitness_history[-1],
            'best_fitness': max(self.fitness_history),
            'improvement': self.fitness_history[-1] - self.fitness_history[0],
            'convergence_generation': self._find_convergence(),
            'best_strategy': self.best_individual.to_strategy_rule().to_dict() if self.best_individual else None
        }
    
    def _find_convergence(self, threshold: float = 0.001) -> int:
        """找到收敛代数"""
        if len(self.fitness_history) < 10:
            return len(self.fitness_history)
        
        for i in range(10, len(self.fitness_history)):
            recent = self.fitness_history[i-10:i]
            if max(recent) - min(recent) < threshold:
                return i
        
        return len(self.fitness_history)


class GridSearchOptimizer:
    """
    网格搜索优化器
    
    作为遗传算法的替代，用于小规模参数搜索
    """
    
    def __init__(self):
        pass
    
    def optimize(
        self,
        base_rule: StrategyRule,
        factor_data: pd.DataFrame,
        returns: pd.Series,
        param_grid: Dict[str, List[float]],
        fitness_func: Callable = None
    ) -> Tuple[StrategyRule, float]:
        """
        网格搜索优化
        
        Args:
            base_rule: 基础规则
            factor_data: 因子数据
            returns: 收益数据
            param_grid: 参数网格 {factor: [threshold1, threshold2, ...]}
            fitness_func: 适应度函数
            
        Returns:
            (最优规则, 最优适应度)
        """
        if fitness_func is None:
            fitness_func = GAOptimizer()._default_fitness
        
        best_rule = None
        best_fitness = -float('inf')
        
        # 对每个参数组合进行评估
        factors = list(param_grid.keys())
        
        from itertools import product
        
        param_combinations = list(product(*[param_grid[f] for f in factors]))
        
        logger.info(f"网格搜索: 共{len(param_combinations)}种参数组合")
        
        for params in param_combinations:
            # 创建新规则
            new_rule = copy.deepcopy(base_rule)
            
            # 更新阈值
            param_dict = dict(zip(factors, params))
            for condition in new_rule.conditions:
                if condition.factor in param_dict:
                    condition.threshold = param_dict[condition.factor]
            
            # 评估
            fitness = fitness_func(new_rule, factor_data, returns)
            
            if fitness > best_fitness:
                best_fitness = fitness
                best_rule = new_rule
        
        logger.info(f"网格搜索完成: 最优适应度 = {best_fitness:.4f}")
        
        return best_rule, best_fitness
