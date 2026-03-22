"""
Species Classifier using LLM API
判断物种是否为 Southeast Asia indigenous、invasive、edible
"""

import os
import json
import time
import requests
from typing import Optional, Dict, List, Tuple
from pathlib import Path
import hashlib
import re


class SpeciesClassifier:
    """LLM API 物种分类器"""

    # 已知的 Singapore/Malaysia 本土植物列表（用于快速筛选）
    KNOWN_INDIGENOUS = {
        # 蔬菜和食用植物
        'Cocos nucifera',  # Coconut
        'Musa × paradisiaca',  # Banana
        'Artocarpus altilis',  # Breadfruit
        'Artocarpus heterophyllus',  # Jackfruit
        'Durio zibethinus',  # Durian
        'Nephelium lappaceum',  # Rambutan
        'Mangifera indica',  # Mango
        'Psidium guajava',  # Guava
        'Averrhoa carambola',  # Starfruit
        'Carica papaya',  # Papaya
        'Annona muricata',  # Soursop
        'Barringtonia racemosa',  # Putat
        'Ficus',  # Fig species
        'Senna alata',  # Ringworm bush (medicinal)
        'Costus',  # Spiral ginger (some species)
        'Curcuma',  # Turmeric
        'Zingiber',  # Ginger
        'Alpinia',  # Galangal
        'Kaempferia',  # Sand ginger
        'Ocimum tenuiflorum',  # Holy basil
        'Centella asiatica',  # Pegaga
        'Vernonia amygdalina',  # Bitter leaf
        'Murraya koenigii',  # Curry leaf
        'Polygonum odoratum',  # Vietnamese coriander
        'Persicaria odorata',  # Laksa leaf
        'Oenanthe javanica',  # Water dropwort
        'Ipomoea aquatica',  # Kangkong
        'Brassica rapa',  # Chinese cabbage
        'Raphanus sativus',  # Radish
        'Phaseolus vulgaris',  # Common bean
        'Vigna unguiculata',  # Cowpea
        'Glycine max',  # Soybean
        'Cucumis sativus',  # Cucumber
        'Citrullus lanatus',  # Watermelon
        'Benincasa hispida',  # Winter melon
        'Luffa',  # Luffa/Loofah
        'Momordica charantia',  # Bitter melon
        'Trichosanthes',  # Snake gourd
        'Sechium edule',  # Chayote
        'Solanum melongena',  # Eggplant
        'Capsicum annuum',  # Chili pepper
        'Solanum lycopersicum',  # Tomato
        'Allium fistulosum',  # Welsh onion
        'Allium sativum',  # Garlic
        'Allium cepa',  # Onion
        'Coriandrum sativum',  # Coriander
        'Eryngium foetidum',  # Sawtooth coriander
        'Apium graveolens',  # Celery
        'Daucus carota',  # Carrot
        'Dysphania ambrosioides',  # Mexican tea
        'Arachis hypogaea',  # Peanut
        'Vigna radiata',  # Mung bean
        'Vigna mungo',  # Black gram
        'Cajanus cajan',  # Pigeon pea
        'Lablab purpureus',  # Hyacinth bean
        'Psophocarpus tetragonolobus',  # Winged bean
        'Pachyrhizus erosus',  # Jicama
        'Colocasia esculenta',  # Taro
        'Dioscorea alata',  # Purple yam
        'Dioscorea hispida',  # Bitter yam
        'Maranta arundinacea',  # Arrowroot
        'Saccharum officinarum',  # Sugarcane
        'Mentha',  # Mint
        'Cymbopogon',  # Lemongrass
        'Pandanus amaryllifolius',  # Pandan
        'Citrus hystrix',  # Kaffir lime
        'Citrus aurantifolia',  # Key lime
        'Aloe vera',  # Aloe
        'Hibiscus sabdariffa',  # Roselle
        'Moringa oleifera',  # Drumstick tree
        'Sauropus androgynus',  # Katuk
        'Gynura procumbens',  # Longevity spinach
        'Strobilanthes reptans',  # 某些种类可食用
    }

    # 已知的入侵物种
    KNOWN_INVASIVE = {
        'Mikania micrantha',  # Mile-a-minute weed
        'Chromolaena odorata',  # Siam weed
        'Lantana camara',  # Lantana
        'Parthenium hysterophorus',  # Parthenium
        'Mimosa pigra',  # Giant sensitive plant
        'Salvinia molesta',  # Giant salvinia
        'Eichhornia crassipes',  # Water hyacinth
        'Pueraria montana',  # Kudzu
        'Ageratina adenophora',  # Crofton weed
        'Clidemia hirta',  # Koster's curse
        'Hedychium gardnerianum',  # Kahili ginger
        'Ardisia elliptica',  # Shoebutton ardisia
        'Psidium cattleianum',  # Strawberry guava
        'Schinus terebinthifolia',  # Brazilian pepper
        'Acacia mearnsii',  # Black wattle
        'Leucaena leucocephala',  # Lead tree
        'Prosopis juliflora',  # Mesquite
        'Eupatorium',  # Some species invasive
        'Antigonon leptopus',  # Coral vine - potentially invasive
    }

    # 可食用植物分类
    EDIBLE_CATEGORIES = {
        'leafy': ['spinach', 'lettuce', 'kale', 'cabbage', 'chard', 'bok choy', 'kangkong', 'pegaga'],
        'root': ['carrot', 'radish', 'potato', 'sweet potato', 'taro', 'yam', 'cassava', 'jicama'],
        'fruit': ['tomato', 'pepper', 'eggplant', 'cucumber', 'melon', 'squash', 'pumpkin'],
        'herb': ['basil', 'mint', 'coriander', 'parsley', 'lemongrass', 'ginger', 'turmeric', 'galangal'],
        'legume': ['bean', 'pea', 'lentil', 'soybean', 'peanut'],
    }

    def __init__(self, api_key: Optional[str] = None, cache_dir: str = "cache/species"):
        """
        初始化物种分类器

        Args:
            api_key: LLM API Key (支持 Anthropic 兼容 API)
            cache_dir: 缓存目录
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY")
        self.api_base = os.environ.get("ANTHROPIC_API_BASE", "https://api.anthropic.com")
        self.model = os.environ.get("LLM_MODEL", "claude-3-haiku-20240307")

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.calls_made = 0
        self.cache_hits = 0

    def _get_cache_path(self, taxon_name: str) -> Path:
        """生成缓存文件路径"""
        safe_name = re.sub(r'[^\w\-]', '_', taxon_name)
        return self.cache_dir / f"{safe_name}.json"

    def _load_cache(self, cache_path: Path) -> Optional[Dict]:
        """从缓存加载数据"""
        if cache_path.exists():
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def _save_cache(self, cache_path: Path, data: Dict):
        """保存数据到缓存"""
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _call_llm(self, prompt: str) -> Optional[str]:
        """调用 LLM API (Anthropic-compatible)"""
        if not self.api_key:
            return None

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }

        data = {
            "model": self.model,
            "max_tokens": 500,
            "system": "You are a botanist specializing in Southeast Asian flora. Provide concise, accurate answers in JSON format.",
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }

        try:
            response = requests.post(
                f"{self.api_base}/v1/messages",
                headers=headers,
                json=data,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            self.calls_made += 1
            return result['content'][0]['text']

        except Exception as e:
            print(f"LLM API call failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            return None

    def classify_species(self, taxon_name: str, common_name: Optional[str] = None) -> Dict:
        """
        分类物种

        Args:
            taxon_name: 学名
            common_name: 俗名

        Returns:
            分类结果字典
        """
        # 检查缓存
        cache_path = self._get_cache_path(taxon_name)
        cached = self._load_cache(cache_path)
        if cached:
            self.cache_hits += 1
            return cached

        # 快速检查已知物种
        result = {
            'taxon_name': taxon_name,
            'common_name': common_name,
            'is_indigenous': None,
            'is_invasive': None,
            'is_edible': None,
            'edible_type': None,
            'confidence': 'low',
            'source': 'unknown'
        }

        # 检查已知本土物种
        for known in self.KNOWN_INDIGENOUS:
            if known.lower() in taxon_name.lower() or taxon_name.lower() in known.lower():
                result['is_indigenous'] = True
                result['source'] = 'known_list'
                result['confidence'] = 'high'
                break

        # 检查已知入侵物种
        for known in self.KNOWN_INVASIVE:
            if known.lower() in taxon_name.lower() or taxon_name.lower() in known.lower():
                result['is_invasive'] = True
                result['source'] = 'known_list'
                result['confidence'] = 'high'
                break

        # 如果不在已知列表中，使用 LLM
        if result['source'] == 'unknown' and self.api_key:
            prompt = f"""Analyze this plant species for Singapore/Southeast Asia context:

Species: {taxon_name}
Common name: {common_name or 'Unknown'}

Answer in JSON format only:
{{
    "is_indigenous": true/false/null,
    "is_invasive": true/false/null,
    "is_edible": true/false/null,
    "edible_type": "leafy/root/fruit/herb/legume/null",
    "notes": "brief explanation"
}}

Consider:
- Indigenous: Native to Southeast Asia, not introduced
- Invasive: Known to be invasive in tropical regions
- Edible: Commonly cultivated or foraged for food"""

            llm_response = self._call_llm(prompt)
            if llm_response:
                try:
                    # 尝试解析 JSON
                    json_match = re.search(r'\{[\s\S]*\}', llm_response)
                    if json_match:
                        llm_result = json.loads(json_match.group())
                        result['is_indigenous'] = llm_result.get('is_indigenous')
                        result['is_invasive'] = llm_result.get('is_invasive')
                        result['is_edible'] = llm_result.get('is_edible')
                        result['edible_type'] = llm_result.get('edible_type')
                        result['confidence'] = 'medium'
                        result['source'] = 'llm'
                        result['notes'] = llm_result.get('notes')
                except json.JSONDecodeError:
                    pass

        # 保存到缓存
        self._save_cache(cache_path, result)
        return result

    def batch_classify(self, species_list: List[Dict], delay: float = 0.5) -> List[Dict]:
        """
        批量分类物种

        Args:
            species_list: 物种列表，每个元素包含 taxon_name 和 common_name
            delay: API 调用间隔（秒）

        Returns:
            分类结果列表
        """
        results = []
        for i, species in enumerate(species_list):
            print(f"Classifying {i+1}/{len(species_list)}: {species.get('taxon_name', 'Unknown')}")

            result = self.classify_species(
                species.get('taxon_name', ''),
                species.get('common_name')
            )
            results.append(result)

            if delay > 0 and self.api_key:
                time.sleep(delay)

        return results

    def get_recommended_species(self, classification_results: List[Dict],
                                  min_area_sqm: float = 10) -> List[Dict]:
        """
        获取推荐种植的物种列表

        Args:
            classification_results: 分类结果列表
            min_area_sqm: 最小面积要求（平方米）

        Returns:
            推荐物种列表
        """
        recommended = []

        for result in classification_results:
            # 筛选条件：
            # 1. 本土或不确定（保守策略）
            # 2. 非入侵物种
            # 3. 可食用或生态价值高

            is_indigenous = result.get('is_indigenous')
            is_invasive = result.get('is_invasive')
            is_edible = result.get('is_edible')

            # 排除入侵物种
            if is_invasive == True:
                continue

            # 优先本土 + 可食用
            if is_indigenous == True and is_edible == True:
                priority = 'high'
            elif is_indigenous == True:
                priority = 'medium'
            elif is_edible == True:
                priority = 'medium'
            elif is_invasive == False:
                priority = 'low'
            else:
                continue

            recommended.append({
                'taxon_name': result['taxon_name'],
                'common_name': result.get('common_name'),
                'is_indigenous': is_indigenous,
                'is_edible': is_edible,
                'edible_type': result.get('edible_type'),
                'priority': priority,
                'min_area_sqm': min_area_sqm,
                'confidence': result.get('confidence', 'low')
            })

        # 按优先级排序
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        recommended.sort(key=lambda x: priority_order.get(x['priority'], 3))

        return recommended

    def get_stats(self) -> Dict:
        """获取 API 调用统计"""
        return {
            'calls_made': self.calls_made,
            'cache_hits': self.cache_hits,
            'total_requests': self.calls_made + self.cache_hits
        }


def main():
    """测试物种分类器"""
    classifier = SpeciesClassifier()

    # 测试物种
    test_species = [
        {'taxon_name': 'Murraya koenigii', 'common_name': 'Curry Leaf'},
        {'taxon_name': 'Centella asiatica', 'common_name': 'Pegaga'},
        {'taxon_name': 'Antigonon leptopus', 'common_name': 'Coral Vine'},
        {'taxon_name': 'Hibiscus sabdariffa', 'common_name': 'Roselle'},
        {'taxon_name': 'Mikania micrantha', 'common_name': 'Mile-a-minute'},
    ]

    results = classifier.batch_classify(test_species)
    recommended = classifier.get_recommended_species(results)

    print("\n=== Classification Results ===")
    for r in results:
        print(f"{r['taxon_name']}:")
        print(f"  Indigenous: {r.get('is_indigenous')}")
        print(f"  Invasive: {r.get('is_invasive')}")
        print(f"  Edible: {r.get('is_edible')}")

    print("\n=== Recommended Species ===")
    for r in recommended:
        print(f"{r['taxon_name']} (Priority: {r['priority']})")

    print(f"\nAPI Stats: {classifier.get_stats()}")


if __name__ == "__main__":
    main()
