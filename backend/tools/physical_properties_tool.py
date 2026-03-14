"""
物理参数查询工具 (Physical Properties Lookup Tool)

用于从JSON数据库中查询材质的物理参数（IOR、颜色、金属度等）
可直接集成到LangChain Agent中作为工具函数
"""

import json
import os
from typing import Any, Dict, List, Optional
from pathlib import Path


class PhysicalPropertiesDatabase:
    """物理属性数据库管理器"""
    
    def __init__(self, json_path: Optional[str] = None):
        """
        初始化数据库
        
        Args:
            json_path: 物理属性JSON文件的路径，默认从data目录查找
        """
        if json_path is None:
            # 自动定位JSON文件路径
            current_dir = Path(__file__).parent.parent  # tools -> backend
            json_path = current_dir / "data" / "physical_properties.json"
        
        self.json_path = Path(json_path)
        self.data = self._load_data()
    
    def _load_data(self) -> Dict[str, Any]:
        """加载JSON数据"""
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"物理属性数据文件未找到: {self.json_path}")
        except json.JSONDecodeError:
            raise ValueError(f"物理属性JSON文件格式错误: {self.json_path}")
    
    def search_material(self, material_name: str) -> Optional[Dict[str, Any]]:
        """
        按名称搜索材质
        
        Args:
            material_name: 材质名称（英文key）
            
        Returns:
            材质属性字典，如果未找到返回None
        """
        material_name = material_name.lower().strip()
        
        # 遍历所有分类查找材质
        for category_key, category_data in self.data.get("materials", {}).items():
            items = category_data.get("items", {})
            if material_name in items:
                result = items[material_name].copy()
                result['category'] = category_data.get('category_name', category_key)
                return result
        
        return None
    
    def get_all_materials(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有材质（扁平化结构）
        
        Returns:
            {material_name: properties} 的字典
        """
        all_materials = {}
        for category_data in self.data.get("materials", {}).values():
            all_materials.update(category_data.get("items", {}))
        return all_materials
    
    def fuzzy_search(self, query: str, threshold: float = 0.6) -> List[Dict[str, Any]]:
        """
        模糊搜索（为后续可能的改进预留）
        
        Args:
            query: 搜索查询字符串
            threshold: 匹配阈值
            
        Returns:
            匹配的材质列表
        """
        query = query.lower()
        results = []
        
        for material_name, properties in self.get_all_materials().items():
            # 简单的包含匹配
            if query in material_name or query in properties.get('description', '').lower():
                results.append({
                    'name': material_name,
                    **properties
                })
        
        return results
    
    def get_category(self, category_key: str) -> Dict[str, Any]:
        """
        获取某个分类的所有材质
        
        Args:
            category_key: 分类键（如 'metals', 'dielectrics'）
            
        Returns:
            该分类的材质字典
        """
        category = self.data.get("materials", {}).get(category_key, {})
        return category.get("items", {})
    
    def get_categories(self) -> List[str]:
        """获取所有分类列表"""
        return list(self.data.get("materials", {}).keys())
    
    def get_property(self, material_name: str, property_key: str, default: Any = None) -> Any:
        """
        获取材质的单个属性
        
        Args:
            material_name: 材质名称
            property_key: 属性键（如 'ior', 'metallic'）
            default: 默认值
            
        Returns:
            属性值或默认值
        """
        material = self.search_material(material_name)
        if material:
            return material.get(property_key, default)
        return default
    
    def validate_properties(self, properties: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        验证属性字典的有效性
        
        Args:
            properties: 待验证的属性字典
            
        Returns:
            (是否有效, 错误列表)
        """
        errors = []
        
        # 检查IOR范围
        if 'ior' in properties:
            ior = properties['ior']
            if not isinstance(ior, (int, float)) or ior <= 0:
                errors.append(f"IOR值无效: {ior}（应为正数）")
        
        # 检查金属度范围
        if 'metallic' in properties:
            metallic = properties['metallic']
            if not isinstance(metallic, (int, float)) or not (0 <= metallic <= 1):
                errors.append(f"Metallic值无效: {metallic}（应在0-1之间）")
        
        # 检查颜色格式
        if 'base_color' in properties:
            color = properties['base_color']
            if not isinstance(color, list) or len(color) not in [3, 4]:
                errors.append(f"Base color格式无效: {color}（应为RGB或RGBA数组）")
            else:
                for c in color:
                    if not isinstance(c, (int, float)) or not (0 <= c <= 1):
                        errors.append(f"Base color通道值无效: {c}（应在0-1之间）")
        
        return len(errors) == 0, errors


# 全局数据库实例
_db_instance: Optional[PhysicalPropertiesDatabase] = None


def get_database() -> PhysicalPropertiesDatabase:
    """获取全局数据库实例（单例模式）"""
    global _db_instance
    if _db_instance is None:
        _db_instance = PhysicalPropertiesDatabase()
    return _db_instance


# ==================== LangChain 工具函数 ====================

def lookup_material_properties(material_name: str) -> str:
    """
    查询材质物理属性
    
    Args:
        material_name: 材质名称（英文，如 'gold', 'glass'）
        
    Returns:
        格式化的属性字符串，可直接用于Agent
    """
    db = get_database()
    material = db.search_material(material_name)
    
    if not material:
        available = ', '.join(db.get_all_materials().keys())
        return f"未找到材质: {material_name}\n\n可用材质: {available}"
    
    # 格式化输出
    result = f"📦 材质: {material.get('name', material_name)}\n"
    result += f"分类: {material.get('category', '未分类')}\n"
    result += f"描述: {material.get('description', '无描述')}\n\n"
    result += "物理参数:\n"
    result += f"  • IOR (折射率): {material.get('ior', 'N/A')}\n"
    result += f"  • Metallic (金属度): {material.get('metallic', 'N/A')}\n"
    result += f"  • Base Color: {material.get('base_color', 'N/A')}\n"
    result += f"  • Roughness (粗糙度): {material.get('roughness', 'N/A')}\n"
    
    if 'transmission' in material:
        result += f"  • Transmission (透射): {material['transmission']}\n"
    
    if 'subsurface' in material:
        result += f"  • Subsurface (次表面): {material['subsurface']}\n"
    
    return result


def search_materials_by_keyword(keyword: str) -> str:
    """
    按关键词搜索材质
    
    Args:
        keyword: 搜索关键词
        
    Returns:
        匹配的材质列表
    """
    db = get_database()
    results = db.fuzzy_search(keyword)
    
    if not results:
        return f"未找到包含'{keyword}'的材质"
    
    output = f"找到 {len(results)} 个匹配项:\n"
    for material in results[:10]:  # 限制显示10个
        output += f"  • {material.get('name', material['name'])}\n"
    
    return output


def get_material_by_property(property_key: str, property_value: Any) -> str:
    """
    按属性查询材质
    
    Args:
        property_key: 属性键（如 'metallic'）
        property_value: 属性值
        
    Returns:
        符合条件的材质列表
    """
    db = get_database()
    all_materials = db.get_all_materials()
    
    matching = []
    for name, props in all_materials.items():
        if props.get(property_key) == property_value:
            matching.append(name)
    
    if not matching:
        return f"未找到 {property_key}={property_value} 的材质"
    
    output = f"找到 {len(matching)} 个 {property_key}={property_value} 的材质:\n"
    for name in matching:
        output += f"  • {name}\n"
    
    return output


def list_all_categories() -> str:
    """列出所有材质分类"""
    db = get_database()
    categories = db.get_categories()
    
    output = "可用的材质分类:\n"
    for category_key in categories:
        category_data = db.data['materials'][category_key]
        output += f"  • {category_data.get('category_name', category_key)}\n"
    
    return output


def list_category_materials(category_key: str) -> str:
    """列出某个分类的所有材质"""
    db = get_database()
    materials = db.get_category(category_key)
    
    if not materials:
        return f"分类不存在或为空: {category_key}"
    
    output = f"分类 '{category_key}' 的材质列表:\n"
    for name, props in materials.items():
        output += f"  • {name}: {props.get('description', '无描述')}\n"
    
    return output


def extract_and_enrich_materials(user_input: str) -> str:
    """
    智能检测用户输入中提到的材质，并返回富化的信息
    
    Args:
        user_input: 用户输入的文本
        
    Returns:
        包含材质信息的富化文本
    """
    if not user_input:
        return user_input
    
    db = get_database()
    user_text_lower = user_input.lower()
    all_materials = db.get_all_materials()
    
    detected_materials = []
    for material_name in all_materials.keys():
        if material_name in user_text_lower:
            detected_materials.append(material_name)
    
    if not detected_materials:
        return user_input
    
    # 构建富化的信息
    enriched = user_input + "\n\n" + "="*70 + "\n"
    enriched += "【自动检测到的材质信息】\n" + "="*70 + "\n\n"
    
    for material_name in detected_materials:
        material_info = lookup_material_properties(material_name)
        enriched += material_info + "\n"
    
    return enriched


if __name__ == "__main__":
    # 测试脚本
    print("=== 物理属性数据库测试 ===\n")
    
    print("1. 查询单个材质:")
    print(lookup_material_properties("gold"))
    print("\n" + "="*50 + "\n")
    
    print("2. 搜索材质:")
    print(search_materials_by_keyword("玻璃"))
    print("\n" + "="*50 + "\n")
    
    print("3. 列出分类:")
    print(list_all_categories())
    print("\n" + "="*50 + "\n")
    
    print("4. 列出金属分类:")
    print(list_category_materials("metals"))
