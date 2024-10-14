from flask import Flask, jsonify, request

app = Flask(__name__)

# 新增一个测试路由
@app.route('/test', methods=['GET'])
def test():
    return "Hello, World!"  # 返回简单的字符串

@app.route('/update_peer_data', methods=['POST'])
def update_peer_data():
    global peer_data
    print("Received data:", request.json)  # 打印接收到的数据
    peer_data = request.json
    return jsonify({"message": "Data received!"}), 200

# 如果需要，可以保留原有的获取数据路由
@app.route('/get_peer_data', methods=['GET'])
def get_peer_data():
    return jsonify(peer_data)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)  # 监听所有网络接口
