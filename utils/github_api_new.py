"""GitHub API 工具模块。"""

import logging
from typing import Optional, Dict
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_repository_info(owner: str, repo: str, token: Optional[str] = None) -> Optional[Dict]:
    """从 GitHub API 获取指定仓库的基本信息。

    Args:
        owner: 仓库所有者用户名。
        repo: 仓库名称。
        token: 可选的 GitHub API 访问令牌，用于增加请求限制。

    Returns:
        包含仓库信息的字典，包括 star 数、fork 数、描述等，
        请求失败时返回 None。
    """
    url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {"Accept": "application/vnd.github.v3+json"}
    
    if token:
        headers["Authorization"] = f"token {token}"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        repo_info = {
            "owner": owner,
            "repo": repo,
            "stars": data.get("stargazers_count", 0),
            "forks": data.get("forks_count", 0),
            "description": data.get("description", ""),
            "full_name": data.get("full_name", ""),
            "html_url": data.get("html_url", ""),
            "language": data.get("language", ""),
            "topics": data.get("topics", []),
            "updated_at": data.get("updated_at", "")
        }
        
        logger.info(f"成功获取仓库 {owner}/{repo} 信息: {repo_info['stars']} stars")
        return repo_info
        
    except requests.exceptions.RequestException as e:
        logger.error(f"获取仓库 {owner}/{repo} 信息失败: {str(e)}")
        return None
