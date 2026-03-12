"""
机器学习模块

提供自动化预测模型训练和评估功能。

示例:
    >>> from quant_assistant.ml import MLPredictor
    >>> predictor = MLPredictor()
    >>> predictor.train(data, target='close')
    >>> predictions = predictor.predict(test_data)
"""

from quant_assistant.ml.predictor import MLPredictor
from quant_assistant.ml.features import FeatureEngineer
from quant_assistant.ml.evaluation import ModelEvaluator

__all__ = [
    'MLPredictor',
    'FeatureEngineer',
    'ModelEvaluator',
]
