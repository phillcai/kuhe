import difflib
from typing import List, Tuple, Dict
import re
from collections import Counter


class StringSimilarity:
    """字符串相似度比较器"""
    
    def __init__(self):
        """初始化字符串相似度比较器"""
        pass
    
    def levenshtein_distance(self, s1: str, s2: str) -> int:
        """
        计算编辑距离（Levenshtein距离）
        
        Args:
            s1: 第一个字符串
            s2: 第二个字符串
            
        Returns:
            编辑距离
        """
        if len(s1) < len(s2):
            return self.levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def levenshtein_similarity(self, s1: str, s2: str) -> float:
        """
        基于编辑距离计算相似度
        
        Args:
            s1: 第一个字符串
            s2: 第二个字符串
            
        Returns:
            相似度（0-1之间）
        """
        max_len = max(len(s1), len(s2))
        if max_len == 0:
            return 1.0
        
        distance = self.levenshtein_distance(s1, s2)
        return 1 - (distance / max_len)
    
    def jaccard_similarity(self, s1: str, s2: str) -> float:
        """
        计算Jaccard相似度（基于字符集合）
        
        Args:
            s1: 第一个字符串
            s2: 第二个字符串
            
        Returns:
            Jaccard相似度（0-1之间）
        """
        set1 = set(s1)
        set2 = set(s2)
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        if union == 0:
            return 1.0
        
        return intersection / union
    
    def cosine_similarity(self, s1: str, s2: str) -> float:
        """
        计算余弦相似度（基于字符频率）
        
        Args:
            s1: 第一个字符串
            s2: 第二个字符串
            
        Returns:
            余弦相似度（0-1之间）
        """
        counter1 = Counter(s1)
        counter2 = Counter(s2)
        
        # 获取所有字符
        all_chars = set(counter1.keys()).union(set(counter2.keys()))
        
        # 构建向量
        vec1 = [counter1.get(char, 0) for char in all_chars]
        vec2 = [counter2.get(char, 0) for char in all_chars]
        
        # 计算点积
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        
        # 计算模长
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def sequence_matcher_similarity(self, s1: str, s2: str) -> float:
        """
        使用difflib的SequenceMatcher计算相似度
        
        Args:
            s1: 第一个字符串
            s2: 第二个字符串
            
        Returns:
            相似度（0-1之间）
        """
        return difflib.SequenceMatcher(None, s1, s2).ratio()
    
    def number_pattern_similarity(self, s1: str, s2: str) -> float:
        """
        基于数字模式的相似度（专门针对类似"27_64_147_95"的格式）
        
        Args:
            s1: 第一个字符串
            s2: 第二个字符串
            
        Returns:
            相似度（0-1之间）
        """
        # 提取数字
        nums1 = re.findall(r'\d+', s1)
        nums2 = re.findall(r'\d+', s2)
        
        # 转换为整数列表
        try:
            nums1 = [int(x) for x in nums1]
            nums2 = [int(x) for x in nums2]
        except ValueError:
            return 0.0
        
        if not nums1 or not nums2:
            return 0.0
        
        # 计算数字序列的相似度
        max_len = max(len(nums1), len(nums2))
        min_len = min(len(nums1), len(nums2))
        
        # 长度相似度
        length_similarity = min_len / max_len
        
        # 数字匹配度
        matches = 0
        for i in range(min_len):
            if nums1[i] == nums2[i]:
                matches += 1
        
        position_similarity = matches / max_len if max_len > 0 else 0
        
        # 数字集合相似度
        set1 = set(nums1)
        set2 = set(nums2)
        set_similarity = len(set1.intersection(set2)) / len(set1.union(set2)) if set1.union(set2) else 0
        
        # 综合相似度
        return 0.4 * position_similarity + 0.3 * length_similarity + 0.3 * set_similarity
    
    def prefix_similarity(self, s1: str, s2: str, separator: str = '_') -> float:
        """
        计算前缀相似度（开头部分越接近越好）
        
        Args:
            s1: 第一个字符串
            s2: 第二个字符串
            separator: 分隔符
            
        Returns:
            前缀相似度（0-1之间）
        """
        # 按分隔符分割
        parts1 = s1.split(separator)
        parts2 = s2.split(separator)
        
        if not parts1 or not parts2:
            return 0.0
        
        max_len = max(len(parts1), len(parts2))
        min_len = min(len(parts1), len(parts2))
        
        # 计算从开头开始连续匹配的部分数量
        consecutive_matches = 0
        for i in range(min_len):
            if parts1[i] == parts2[i]:
                consecutive_matches += 1
            else:
                break
        
        # 前缀匹配得分（连续匹配的权重更高）
        if consecutive_matches == 0:
            prefix_score = 0.0
        else:
            # 使用指数权重，开头匹配更重要
            prefix_score = consecutive_matches / max_len
            # 给连续匹配额外加权
            bonus = (consecutive_matches / min_len) ** 0.5
            prefix_score = min(1.0, prefix_score * (1 + bonus))
        
        return prefix_score
    
    def comprehensive_similarity(self, s1: str, s2: str) -> float:
        """
        综合相似度计算（多种算法加权平均，重视前缀匹配）
        
        Args:
            s1: 第一个字符串
            s2: 第二个字符串
            
        Returns:
            综合相似度（0-1之间）
        """
        levenshtein_sim = self.levenshtein_similarity(s1, s2)
        jaccard_sim = self.jaccard_similarity(s1, s2)
        cosine_sim = self.cosine_similarity(s1, s2)
        sequence_sim = self.sequence_matcher_similarity(s1, s2)
        number_sim = self.number_pattern_similarity(s1, s2)
        prefix_sim = self.prefix_similarity(s1, s2)
        
        # 调整权重分配，重视前缀匹配
        weights = {
            'prefix': 0.40,        # 前缀匹配权重最高
            'levenshtein': 0.20,   # 编辑距离
            'sequence': 0.15,      # 序列匹配
            'number_pattern': 0.15, # 数字模式
            'jaccard': 0.05,       # 字符集合
            'cosine': 0.05         # 字符频率
        }
        
        comprehensive_sim = (
            weights['prefix'] * prefix_sim +
            weights['levenshtein'] * levenshtein_sim +
            weights['jaccard'] * jaccard_sim +
            weights['cosine'] * cosine_sim +
            weights['sequence'] * sequence_sim +
            weights['number_pattern'] * number_sim
        )
        
        return comprehensive_sim
    
    def calculate_all_similarities(self, s1: str, s2: str) -> Dict[str, float]:
        """
        计算所有类型的相似度
        
        Args:
            s1: 第一个字符串
            s2: 第二个字符串
            
        Returns:
            包含所有相似度类型的字典
        """
        return {
            'prefix': self.prefix_similarity(s1, s2),
            'levenshtein': self.levenshtein_similarity(s1, s2),
            'jaccard': self.jaccard_similarity(s1, s2),
            'cosine': self.cosine_similarity(s1, s2),
            'sequence_matcher': self.sequence_matcher_similarity(s1, s2),
            'number_pattern': self.number_pattern_similarity(s1, s2),
            'comprehensive': self.comprehensive_similarity(s1, s2)
        }
    
    def rank_similarities(self, target: str, candidates: List[str], 
                         method: str = 'comprehensive') -> List[Tuple[str, float]]:
        """
        对候选字符串按相似度排序
        
        Args:
            target: 目标字符串
            candidates: 候选字符串列表
            method: 相似度计算方法
            
        Returns:
            按相似度降序排列的(字符串, 相似度)元组列表
        """
        similarities = []
        
        for candidate in candidates:
            if method == 'comprehensive':
                sim = self.comprehensive_similarity(target, candidate)
            elif method == 'prefix':
                sim = self.prefix_similarity(target, candidate)
            elif method == 'levenshtein':
                sim = self.levenshtein_similarity(target, candidate)
            elif method == 'jaccard':
                sim = self.jaccard_similarity(target, candidate)
            elif method == 'cosine':
                sim = self.cosine_similarity(target, candidate)
            elif method == 'sequence_matcher':
                sim = self.sequence_matcher_similarity(target, candidate)
            elif method == 'number_pattern':
                sim = self.number_pattern_similarity(target, candidate)
            else:
                sim = self.comprehensive_similarity(target, candidate)
            
            similarities.append((candidate, sim))
        
        # 按相似度降序排序
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities


def main():
    """主函数 - 演示字符串相似度比较"""
    # 创建相似度比较器
    similarity_calculator = StringSimilarity()
    
    # 目标字符串
    target =    "23_67_41_89_15",
    
    # 候选字符串列表（用户新提供的列表）
    ccandidates = [
     
        "23_67_41_15_89",
        "23_67_89_41_15",
        "23_67_89_15_41",
        "23_67_15_41_89",
        "23_67_15_89_41",
        "23_41_67_89_15",
        "23_41_67_15_89",
        "23_41_89_67_15",
        "23_41_89_15_67",
        "23_41_15_67_89",
        "23_41_15_89_67",
        "23_89_67_41_15",
        "23_89_67_15_41",
        "23_89_41_67_15",
        "23_89_41_15_67",
        "23_89_15_67_41",
        "23_89_15_41_67",
        "23_15_67_41_89",
        "23_15_67_89_41",
        "23_15_41_67_89",
        "23_15_41_89_67",
        "23_15_89_67_41",
        "23_15_89_41_67",
        "67_23_41_89_15",
        "67_23_41_15_89",
        "67_23_89_41_15",
        "67_23_89_15_41",
        "67_23_15_41_89",
        "67_23_15_89_41",
        "67_41_23_89_15",
        "67_41_23_15_89",
        "67_41_89_23_15",
        "67_41_89_15_23",
        "67_41_15_23_89",
        "67_41_15_89_23",
        "67_89_23_41_15",
        "67_89_23_15_41",
        "67_89_41_23_15",
        "67_89_41_15_23",
        "67_89_15_23_41",
        "67_89_15_41_23",
        "67_15_23_41_89",
        "67_15_23_89_41",
        "67_15_41_23_89",
        "67_15_41_89_23",
        "67_15_89_23_41",
        "67_15_89_41_23",
        "41_23_67_89_15",
        "41_23_67_15_89",
        "41_23_89_67_15",
        "41_23_89_15_67",
        "41_23_15_67_89",
        "41_23_15_89_67",
        "41_67_23_89_15",
        "41_67_23_15_89",
        "41_67_89_23_15",
        "41_67_89_15_23",
        "41_67_15_23_89",
        "41_67_15_89_23",
        "41_89_23_67_15",
        "41_89_23_15_67",
        "41_89_67_23_15",
        "41_89_67_15_23",
        "41_89_15_23_67",
        "41_89_15_67_23",
        "41_15_23_67_89",
        "41_15_23_89_67",
        "41_15_67_23_89",
        "41_15_67_89_23",
        "41_15_89_23_67",
        "41_15_89_67_23",
        "89_23_67_41_15",
        "89_23_67_15_41",
        "89_23_41_67_15",
        "89_23_41_15_67",
        "89_23_15_67_41",
        "89_23_15_41_67",
        "89_67_23_41_15",
        "89_67_23_15_41",
        "89_67_41_23_15",
        "89_67_41_15_23",
        "89_67_15_23_41",
        "89_67_15_41_23",
        "89_41_23_67_15",
        "89_41_23_15_67",
        "89_41_67_23_15",
        "89_41_67_15_23",
        "89_41_15_23_67",
        "89_41_15_67_23",
        "89_15_23_67_41",
        "89_15_23_41_67",
        "89_15_67_23_41",
        "89_15_67_41_23",
        "89_15_41_23_67",
        "89_15_41_67_23",
        "15_23_67_41_89",
        "15_23_67_89_41",
        "15_23_41_67_89",
        "15_23_41_89_67",
        "15_23_89_67_41",
        "15_23_89_41_67",
        "15_67_23_41_89",
        "15_67_23_89_41",
        "15_67_41_23_89",
        "15_67_41_89_23",
        "15_67_89_23_41",
        "15_67_89_41_23",
        "15_41_23_67_89",
        "15_41_23_89_67",
        "15_41_67_23_89",
        "15_41_67_89_23",
        "15_41_89_23_67",
        "15_41_89_67_23",
        "15_89_23_67_41",
        "15_89_23_41_67",
        "15_89_67_23_41",
        "15_89_67_41_23",
        "15_89_41_23_67",
        "15_89_41_67_23"
    ]
    
    print(f"=== 字符串相似度比较 ===")
    print(f"目标字符串: {target}")
    print(f"候选字符串数量: {len(candidates)}")
    print()
    
    # 去重候选字符串
    unique_candidates = list(set(candidates))
    print(f"去重后候选字符串数量: {len(unique_candidates)}")
    print("候选字符串列表:")
    for i, candidate in enumerate(unique_candidates, 1):
        print(f"  {i:2d}. {candidate}")
    print()
    
    # 使用不同方法计算相似度并排序
    methods = ['comprehensive', 'prefix', 'levenshtein', 'sequence_matcher']
    
    for method in methods:
        print(f"=== {method.upper()} 方法排序结果 ===")
        ranked_results = similarity_calculator.rank_similarities(target, unique_candidates, method)
        
        for i, (candidate, similarity) in enumerate(ranked_results, 1):
            print(f"{i:2d}. {candidate:20s} - 相似度: {similarity:.4f}")
        print()
    
    # 详细分析最相似的字符串
    print("=== 详细相似度分析 ===")
    best_match = similarity_calculator.rank_similarities(target, unique_candidates, 'comprehensive')[0][0]
    print(f"综合评分最高的字符串: {best_match}")
    
    all_similarities = similarity_calculator.calculate_all_similarities(target, best_match)
    print(f"与目标字符串 '{target}' 的各种相似度:")
    for method, sim in all_similarities.items():
        print(f"  {method:15s}: {sim:.4f}")
    
    # 前缀匹配专项分析
    print("\n=== 前缀匹配专项分析 ===")
    prefix_ranked = similarity_calculator.rank_similarities(target, unique_candidates, 'prefix')
    print(f"前缀匹配最高的字符串: {prefix_ranked[0][0]} (相似度: {prefix_ranked[0][1]:.4f})")
    
    target_parts = target.split('_')
    print(f"目标字符串各部分: {target_parts}")
    print("\n前缀匹配详细分析:")
    
    for candidate, prefix_sim in prefix_ranked[:5]:  # 显示前5名
        candidate_parts = candidate.split('_')
        consecutive_matches = 0
        for i in range(min(len(target_parts), len(candidate_parts))):
            if target_parts[i] == candidate_parts[i]:
                consecutive_matches += 1
            else:
                break
        
        match_info = f"前{consecutive_matches}段匹配" if consecutive_matches > 0 else "无前缀匹配"
        print(f"  {candidate:20s} - {match_info} - 前缀相似度: {prefix_sim:.4f}")
        print(f"    候选字符串各部分: {candidate_parts}")
    
    # 分析数字组成相同的字符串
    print("\n=== 数字组成分析 ===")
    target_numbers = set(target.split('_'))
    print(f"目标字符串包含的数字: {sorted(target_numbers)}")
    
    same_numbers = []
    for candidate in unique_candidates:
        candidate_numbers = set(candidate.split('_'))
        if candidate_numbers == target_numbers:
            same_numbers.append(candidate)
    
    if same_numbers:
        print(f"包含相同数字组合的字符串数量: {len(same_numbers)}")
        print("按综合相似度排序 (重视前缀匹配):")
        comprehensive_ranked = similarity_calculator.rank_similarities(target, same_numbers, 'comprehensive')
        for i, (candidate, comprehensive_sim) in enumerate(comprehensive_ranked, 1):
            prefix_sim = similarity_calculator.prefix_similarity(target, candidate)
            print(f"  {i:2d}. {candidate:20s} - 综合: {comprehensive_sim:.4f}, 前缀: {prefix_sim:.4f}")
    else:
        print("没有找到包含完全相同数字组合的字符串")


if __name__ == "__main__":
    main() 