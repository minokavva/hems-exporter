import socket
import textwrap

ECHONET_PORT = 3610


# ECHONET-Liteから情報取得
def fetch_echonet(edata):
    # ヘッダ
    ehd1 = "10"     # ECHONET-Lite
    ehd2 = "81"     # 規定電文形式
    tid = "0001"    # トランザクションID=1(使わないので固定)
    ehd = ehd1 + ehd2 + tid

    # 受信ソケット準備
    recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    recv_sock.bind(("0.0.0.0", ECHONET_PORT))

    # マルチキャストで送信
    destination_ip = "224.0.23.0"
    send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    send_sock.sendto(bytes.fromhex(ehd + edata), (destination_ip, ECHONET_PORT))
    send_sock.close()

    # 回答受信
    data = recv_sock.recv(1024)
    recv_sock.close()
    
    return data


# 蓄電池
def fetch_battery_metrics():
    # 送信元(自分)
    seoj = "05ff01"     # 管理・操作関連機器クラスグループ/コントローラ/インスタンス01

    # 送信先(蓄電池)
    deoj = "027d01"     # 住宅・設備機関連機器クラスグループ/蓄電池/インスタンス01
    esv = "62"          # プロパティ値読み出し要求
    opc = "02"          # 読み出すプロパティ2件
    prop1 = "d300"      # 瞬時充放電電力計測値/パラメータ0件
    prop2 = "e400"      # 蓄電残量3/パラメータ0件

    # リクエスト送信
    data = fetch_echonet(seoj + deoj + esv + opc + prop1 + prop2)
    
    # プロパティが2つあるはず
    opc_pos = 11
    if data[opc_pos] != 0x2:
        raise Exception(f"回答のプロパティの数が変(opc={data[opc_pos]:#x})")

    # プロパティ取り出し
    return {
        "electricity_flow": int.from_bytes(data[14:18], byteorder="big", signed=True),
        "state_of_charge": int.from_bytes(data[20:21], byteorder="big", signed=False),
    }
 
 
# 太陽光発電
def fetch_pv_metrics():
    # 送信元(自分)
    seoj = "05ff01"     # 管理・操作関連機器クラスグループ/コントローラ/インスタンス01

    # 送信先(太陽光発電)
    deoj = "027901"     # 住宅・設備機関連機器クラスグループ/住宅用太陽光発電/インスタンス01
    esv = "62"          # プロパティ値読み出し要求
    opc = "01"          # 読み出すプロパティ1件
    prop1 = "e000"      # 瞬時充放電電力計測値/パラメータ0件

    # リクエスト送信
    data = fetch_echonet(seoj + deoj + esv + opc + prop1)

    # プロパティが1つあるはず
    opc_pos = 11
    if data[opc_pos] != 0x1:
        raise Exception(f"回答のプロパティの数が変(opc={data[opc_pos]:#x})")

    # プロパティ取り出し
    return {
        "generated_electricity": int.from_bytes(data[14:16], byteorder="big", signed=False),
    }


# ヘルスチェック
def health_check_handler(start_response):
    status_code = "200 OK"
    headers = [("Content-type", "text/plain")]
    start_response(status_code, headers)
    return ["ok".encode("utf-8")]


# メトリクス
def metrics_handler(start_response):
    # 情報取得
    try:
        battery_metrics = fetch_battery_metrics()
        pv_metrics = fetch_pv_metrics()
    except Exception:
        status_code = "500 Internal Server Error"
        headers = [("Content-type", "text/plain")]
        start_response(status_code, headers)
        return ["Failed to fetch metrics from ECHONET-Lite devices".encode("utf-8")]

    # OpenMetrics形式に整形してプレーンテキストでレスポンス
    status_code = "200 OK"
    headers = [("Content-type", "text/plain")]
    start_response(status_code, headers)

    body = f'''
            battery_state_of_charge {battery_metrics["state_of_charge"]}
            battery_electricity_flow {battery_metrics["electricity_flow"]}
            pv_generated_electricity {pv_metrics["generated_electricity"]}
        '''
    return [textwrap.dedent(body)[1:-1].encode("utf-8")]


def app(environ, start_response):
    path = environ["PATH_INFO"]
    
    # ヘルスチェック
    if path == "/healthcheck":
        return health_check_handler(start_response)
    
    # メトリクス
    if path == "/metrics":
        return metrics_handler(start_response)

    # 存在しないパス
    status_code = "404 Not Found"
    headers = [("Content-type", "text/plain")]
    start_response(status_code, headers)
    return ["404".encode("utf-8")]
