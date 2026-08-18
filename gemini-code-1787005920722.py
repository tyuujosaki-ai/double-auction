import random
import time
import pandas as pd
import streamlit as st

# ページ初期設定
st.set_page_config(
    page_title="経済実験：オーラルダブルオークション", layout="wide"
)

# セッション状態の初期化
if "game_started" not in st.session_state:
    st.session_state.game_started = False
if "players" not in st.session_state:
    st.session_state.players = {}  # {name: {'role': ..., 'value': ..., 'traded': ..., 'trade_price': ..., 'point': ...}}
if "bids" not in st.session_state:
    st.session_state.bids = []  # 買い注文 [{'player': ..., 'price': ...}]
if "asks" not in st.session_state:
    st.session_state.asks = []  # 売り注文 [{'player': ..., 'price': ...}]
if "trades" not in st.session_state:
    st.session_state.trades = (
        []
    )  # 成立取引 [{'buyer': ..., 'seller': ..., 'price': ..., 'buyer_point': ..., 'seller_point': ...}]
if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False
if "last_order_msg" not in st.session_state:
    st.session_state.last_order_msg = {}  # 各生徒の最後の注文メッセージ保持用

# 管理画面用パスワード設定
ADMIN_PASSWORD = "admin1234"


def calculate_equilibrium(players):
    """需要と供給から理論上の均衡価格・取引量を計算する"""
    buyers_values = sorted(
        [p["value"] for p in players.values() if p["role"] == "買い手"],
        reverse=True,
    )
    sellers_values = sorted(
        [p["value"] for p in players.values() if p["role"] == "売り手"]
    )

    k = 0
    while k < len(buyers_values) and k < len(sellers_values):
        if buyers_values[k] >= sellers_values[k]:
            k += 1
        else:
            break

    if k == 0:
        return "取引不成立（需要と供給が不一致）", 0

    p_min = max(
        sellers_values[k - 1],
        buyers_values[k]
        if k < len(buyers_values)
        else sellers_values[k - 1],
    )
    p_max = min(
        buyers_values[k - 1],
        sellers_values[k]
        if k < len(sellers_values)
        else buyers_values[k - 1],
    )

    if p_min == p_max:
        eq_price_str = f"{p_min} 円"
    else:
        eq_price_str = f"{p_min} 円 〜 {p_max} 円"

    return eq_price_str, k


# タイトル
st.title("📈 経済実験：市場メカニズムと均衡価格")

# Sidebar: モード切替
mode = st.sidebar.radio("利用モードを選択", ["生徒用画面", "教員用管理画面"])

# ==========================================
# 教員用管理画面
# ==========================================
if mode == "教員用管理画面":
    st.header("⚙️ 教員用 進行・管理ダッシュボード")

    # パスワード認証ブロック
    if not st.session_state.admin_authenticated:
        st.subheader("🔐 管理者認証")
        input_password = st.text_input(
            "教員用パスワードを入力してください", type="password"
        )

        if st.button("ログイン"):
            if input_password == ADMIN_PASSWORD:
                st.session_state.admin_authenticated = True
                st.success("ログインしました。")
                st.rerun()
            else:
                st.error("パスワードが正しくありません。")
    else:
        # ログアウトボタン
        if st.sidebar.button("管理者ログアウト"):
            st.session_state.admin_authenticated = False
            st.rerun()

        # 実験設定・開始パネル
        st.subheader("1. 実験の準備と開始")

        # 1〜41までの全角数字を生成して初期値に設定
        zenkaku_numbers = [
            str(i).translate(str.maketrans("0123456789", "０１２３４５６７８９"))
            for i in range(1, 42)
        ]
        default_students = "\n".join(zenkaku_numbers)

        student_list_input = st.text_area(
            "参加する生徒の名前（または出席番号）を改行区切りで入力してください",
            value=default_students,
            height=200,
        )

        # 価格上限の設定（2100円を初期値として100円刻みで可変）
        col_cfg1, col_cfg2 = st.columns(2)
        with col_cfg1:
            max_price_setting = st.number_input(
                "評価額 / コストの最大値（円）",
                min_value=300,
                max_value=10000,
                value=2100,
                step=100,
            )

        BUYER_MIN, BUYER_MAX = 200, max_price_setting
        SELLER_MIN, SELLER_MAX = 100, max_price_setting

        st.caption(
            f"※ 最小値/最大値: 買い手 ({BUYER_MIN}円〜{BUYER_MAX}円) / 売り手 ({SELLER_MIN}円〜{SELLER_MAX}円) ※100円刻み・各同額なし"
        )

        if st.button("👥 役割割り当て＆実験スタート", type="primary"):
            students = [
                s.strip() for s in student_list_input.split("\n") if s.strip()
            ]
            num_students = len(students)

            if num_students < 2:
                st.error("生徒は2名以上必要です。")
            else:
                shuffled_students = students.copy()
                random.shuffle(shuffled_students)

                half = num_students // 2
                buyers = shuffled_students[:half]
                sellers = shuffled_students[half:]

                # 100円刻みの候補リストを作成
                buyer_candidates = list(range(BUYER_MIN, BUYER_MAX + 1, 100))
                seller_candidates = list(
                    range(SELLER_MIN, SELLER_MAX + 1, 100)
                )

                if len(buyers) > len(buyer_candidates):
                    st.error(
                        f"買い手の人数（{len(buyers)}名）が所持金のバリエーション数（{len(buyer_candidates)}通り）を超えています。最大値を上げるか人数を減らしてください。"
                    )
                elif len(sellers) > len(seller_candidates):
                    st.error(
                        f"売り手の人数（{len(sellers)}名）が生産コストのバリエーション数（{len(seller_candidates)}通り）を超えています。最大値を上げるか人数を減らしてください。"
                    )
                else:
                    # 重複なし（同額なし）でランダム抽出
                    buyer_values = random.sample(
                        buyer_candidates, len(buyers)
                    )
                    seller_values = random.sample(
                        seller_candidates, len(sellers)
                    )

                    players = {}
                    for b, val in zip(buyers, buyer_values):
                        players[b] = {
                            "role": "買い手",
                            "value": val,
                            "traded": False,
                            "trade_price": None,
                            "point": 0,
                        }
                    for s, val in zip(sellers, seller_values):
                        players[s] = {
                            "role": "売り手",
                            "value": val,
                            "traded": False,
                            "trade_price": None,
                            "point": 0,
                        }

                    st.session_state.players = {
                        s: players[s] for s in students if s in players
                    }
                    st.session_state.bids = []
                    st.session_state.asks = []
                    st.session_state.trades = []
                    st.session_state.last_order_msg = {}
                    st.session_state.game_started = True
                    st.success(
                        f"実験を開始しました！（買い手: {len(buyers)}名, 売り手: {len(sellers)}名）"
                    )

        st.divider()

        # リアルタイム監視パネル
        st.subheader("2. 市場の状況（リアルタイム）")

        if st.session_state.game_started and st.session_state.players:
            # 均衡価格（理論値）の計算表示
            eq_price, eq_qty = calculate_equilibrium(st.session_state.players)

            st.info("📊 **【理論値】市場の均衡予想**")
            col_eq1, col_eq2 = st.columns(2)
            with col_eq1:
                st.metric(label="🎯 均衡価格（理論値）", value=eq_price)
            with col_eq2:
                st.metric(
                    label="📦 均衡取引数量（理論値）", value=f"{eq_qty} 件"
                )

        col_a, col_b = st.columns(2)
        with col_a:
            st.write("### 📜 成約履歴")
            if st.session_state.trades:
                df_trades = pd.DataFrame(st.session_state.trades)
                df_trades_display = df_trades.rename(
                    columns={
                        "buyer": "買い手",
                        "seller": "売り手",
                        "price": "取引価格(円)",
                        "buyer_point": "買い手獲得pt",
                        "seller_point": "売り手獲得pt",
                    }
                )
                st.dataframe(df_trades_display, use_container_width=True)
                st.line_chart(df_trades["price"])
            else:
                st.info("まだ取引は成立していません。")

        with col_b:
            st.write("### 👥 参加者一覧と獲得ポイント")
            if st.session_state.players:
                df_players = pd.DataFrame.from_dict(
                    st.session_state.players, orient="index"
                )
                df_players_display = df_players.rename(
                    columns={
                        "role": "役割",
                        "value": "所持金 / コスト",
                        "traded": "取引完了",
                        "trade_price": "約定価格",
                        "point": "獲得ポイント",
                    }
                )
                st.dataframe(df_players_display, use_container_width=True)

        if st.button("実験をリセットする"):
            st.session_state.game_started = False
            st.rerun()

# ==========================================
# 生徒用画面
# ==========================================
else:
    st.header("👤 生徒用 取引画面")

    if not st.session_state.game_started:
        st.warning(
            "教員が実験を開始するまでお待ちください。（自動で確認中...）"
        )
        time.sleep(2)
        st.rerun()
    else:

        def get_sort_key(name):
            half_name = name.translate(
                str.maketrans("０１２３４５６７８９", "0123456789")
            )
            try:
                return (0, int(half_name))
            except ValueError:
                return (1, name)

        player_names = sorted(
            list(st.session_state.players.keys()), key=get_sort_key
        )

        my_name = st.selectbox(
            "あなたの出席番号を選択してください",
            player_names,
            index=None,
            placeholder="選択してください...",
        )

        if my_name:
            my_info = st.session_state.players[my_name]
            role = my_info["role"]
            limit_val = my_info["value"]

            st.info(f"**あなたの役割:** {role}")

            col_m1, col_m2 = st.columns(2)
            with col_m1:
                if role == "買い手":
                    st.metric(
                        label="💰 あなたの所持金（上限価格）",
                        value=f"{limit_val} 円",
                    )
                else:
                    st.metric(
                        label="🏭 あなたの生産コスト（下限価格）",
                        value=f"{limit_val} 円",
                    )
            with col_m2:
                st.metric(
                    label="🏆 あなたの獲得ポイント",
                    value=f"{my_info['point']} pt",
                )

            if role == "買い手":
                st.caption(
                    "※ これより高い金額での購入はできません。安く買うほどポイント（所持金 - 購入額）が高くなります。"
                )
            else:
                st.caption(
                    "※ これより低い金額での売却はできません。高く売るほどポイント（売却額 - コスト）が高くなります。"
                )

            if my_info["traded"]:
                st.success(
                    f"🎉 取引が成立しました！ （約定価格: {my_info['trade_price']} 円 / 獲得ポイント: {my_info['point']} pt）"
                )
            else:
                st.divider()
                st.subheader("注文の発注")

                price_input = st.number_input(
                    "提示する価格（円）",
                    min_value=0,
                    step=100,
                    value=limit_val,
                )

                if st.button("注文する", type="primary"):
                    if role == "買い手" and price_input > limit_val:
                        st.error("所持金を超える金額は提示できません！")
                    elif role == "売り手" and price_input < limit_val:
                        st.error(
                            "生産コストを下回る金額は提示できません！"
                        )
                    else:
                        if role == "買い手":
                            st.session_state.bids.append(
                                {"player": my_name, "price": price_input}
                            )
                        else:
                            st.session_state.asks.append(
                                {"player": my_name, "price": price_input}
                            )

                        st.session_state.last_order_msg[my_name] = f"注文しました！（提示価格: {price_input} 円）"

                        # マッチングロジック
                        valid_bids = [
                            b
                            for b in st.session_state.bids
                            if not st.session_state.players[b["player"]][
                                "traded"
                            ]
                        ]
                        valid_asks = [
                            a
                            for a in st.session_state.asks
                            if not st.session_state.players[a["player"]][
                                "traded"
                            ]
                        ]

                        if valid_bids and valid_asks:
                            max_bid = max(valid_bids, key=lambda x: x["price"])
                            min_ask = min(valid_asks, key=lambda x: x["price"])

                            if max_bid["price"] >= min_ask["price"]:
                                trade_price = (
                                    max_bid["price"] + min_ask["price"]
                                ) // 2

                                buyer_name = max_bid["player"]
                                seller_name = min_ask["player"]

                                buyer_val = st.session_state.players[
                                    buyer_name
                                ]["value"]
                                seller_val = st.session_state.players[
                                    seller_name
                                ]["value"]

                                # ポイント計算（差額）
                                buyer_pt = buyer_val - trade_price
                                seller_pt = trade_price - seller_val

                                # 成立記録更新
                                st.session_state.trades.append(
                                    {
                                        "buyer": buyer_name,
                                        "seller": seller_name,
                                        "price": trade_price,
                                        "buyer_point": buyer_pt,
                                        "seller_point": seller_pt,
                                    }
                                )

                                # 買い手の情報更新
                                st.session_state.players[buyer_name][
                                    "traded"
                                ] = True
                                st.session_state.players[buyer_name][
                                    "trade_price"
                                ] = trade_price
                                st.session_state.players[buyer_name][
                                    "point"
                                ] = buyer_pt

                                # 売り手の情報更新
                                st.session_state.players[seller_name][
                                    "traded"
                                ] = True
                                st.session_state.players[seller_name][
                                    "trade_price"
                                ] = trade_price
                                st.session_state.players[seller_name][
                                    "point"
                                ] = seller_pt

                        st.rerun()

                if my_name in st.session_state.last_order_msg:
                    st.info(st.session_state.last_order_msg[my_name])

            # 市場板情報
            st.divider()
            st.subheader("📊 現在の市場状況（板情報）")
            col_bid, col_ask = st.columns(2)

            with col_bid:
                st.write("**買い注文一覧（高い順）**")
                active_bids = [
                    b
                    for b in st.session_state.bids
                    if not st.session_state.players[b["player"]]["traded"]
                ]
                if active_bids:
                    df_bids = pd.DataFrame(active_bids).sort_values(
                        by="price", ascending=False
                    )
                    st.dataframe(
                        df_bids[["price"]], use_container_width=True
                    )
                else:
                    st.write("買い注文なし")

            with col_ask:
                st.write("**売り注文一覧（安い順）**")
                active_asks = [
                    a
                    for a in st.session_state.asks
                    if not st.session_state.players[a["player"]]["traded"]
                ]
                if active_asks:
                    df_asks = pd.DataFrame(active_asks).sort_values(
                        by="price", ascending=True
                    )
                    st.dataframe(
                        df_asks[["price"]], use_container_width=True
                    )
                else:
                    st.write("売り注文なし")
