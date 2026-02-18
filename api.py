# -*- coding: utf-8 -*-
"""
Web 服务入口：对外仍使用 api:app，便于 uvicorn api:app / Docker CMD 不变。
"""
import os

from web.app import app

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=True)
