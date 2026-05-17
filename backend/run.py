
if __name__ == "__main__":

    import uvicorn

    print("正在启动 DataArk 后端...")
    print(f"健康检查: http://localhost:8000/api/v1/health")
    print(f"停止: python run.py --stop")
    print("─" * 40)
    uvicorn.run(
        "app.main:app",
        host="localhost",
        port=8000,
    )
