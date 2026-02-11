import time
import hashlib
import urllib.parse
import requests
from typing import Tuple, Dict, Any, Optional


class WBIManager:
    """WBI签名管理器 - 统一管理B站WBI签名"""
    
    MIXIN_KEY_ENC_TAB = [
        46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
        33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
        61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
        36, 20, 34, 44, 52
    ]
    
    BACKUP_SALT = "ea1db124af3c7062474693fa704f4ff8"
    
    def __init__(self, header: Dict[str, str]):
        self.header = header
        self._img_key: Optional[str] = None
        self._sub_key: Optional[str] = None
        self._key_refresh_time: float = 0
        self._key_cache_duration = 3600  # 缓存1小时
    
    def _get_wbi_keys(self) -> Tuple[Optional[str], Optional[str]]:
        """动态获取 WBI 签名所需的 img_key 和 sub_key"""
        current_time = time.time()
        
        if (self._img_key and self._sub_key and 
            current_time - self._key_refresh_time < self._key_cache_duration):
            return self._img_key, self._sub_key
        
        try:
            resp = requests.get(
                "https://api.bilibili.com/x/web-interface/nav",
                headers=self.header,
                timeout=5
            )
            resp.raise_for_status()
            json_content = resp.json()
            img_url = json_content['data']['wbi_img']['img_url']
            sub_url = json_content['data']['wbi_img']['sub_url']
            self._img_key = img_url.rsplit('/', 1)[1].split('.')[0]
            self._sub_key = sub_url.rsplit('/', 1)[1].split('.')[0]
            self._key_refresh_time = current_time
            return self._img_key, self._sub_key
        except Exception as e:
            print(f"[WBI] 动态获取 WBI keys 失败: {e}，将使用备用盐值")
            return None, None
    
    def _md5(self, code: str) -> str:
        """MD5哈希"""
        md5 = hashlib.md5()
        md5.update(code.encode('utf-8'))
        return md5.hexdigest()
    
    def sign(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """为请求参数添加 WBI 签名"""
        img_key, sub_key = self._get_wbi_keys()
        
        if img_key and sub_key:
            return self._enc_wbi(params, img_key, sub_key)
        else:
            return self._sign_with_backup_salt(params)
    
    def _enc_wbi(self, params: Dict[str, Any], img_key: str, sub_key: str) -> Dict[str, Any]:
        """使用动态获取的key进行WBI签名"""
        raw_key = img_key + sub_key
        mixin_key = "".join([raw_key[i] for i in self.MIXIN_KEY_ENC_TAB])[:32]
        curr_time = int(time.time())
        params['wts'] = curr_time
        params = dict(sorted(params.items()))
        
        params = {
            k: "".join([char for char in str(v) if char not in "!'()*"])
            for k, v in params.items()
        }
        
        query = urllib.parse.urlencode(params)
        w_rid = self._md5(query + mixin_key)
        params['w_rid'] = w_rid
        return params
    
    def _sign_with_backup_salt(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """使用备用盐值进行签名（兼容旧版本）"""
        params['wts'] = int(time.time())
        query_for_w_rid = urllib.parse.urlencode(sorted(params.items()))
        w_rid = self._md5(query_for_w_rid + self.BACKUP_SALT)
        params['w_rid'] = w_rid
        return params
    
    def refresh_keys(self):
        """强制刷新WBI keys"""
        self._img_key = None
        self._sub_key = None
        self._key_refresh_time = 0
