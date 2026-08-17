import random
import pandas as pd
import streamlit as st

# ページ初期設定
st.set_page_config(page_title="経済実験：オーラルダブルオークション", layout="wide")

# セッション状態の初期化
if "game_state" not in st.groupby if hasattr(st, "groupby") else st.session_state:
    st.session_state.game_started = False
    st.session_state.players = {}  # {name: {'role': ..., 'value': ...}}
    st.session_state.bids = []  # 買い注文 [{'player': ..., 'price': ...}]
    st.session_state.asks = []  # 売り注文 [{'player': ..., 'price': ...}]
    st.session_state.trades = []  # 成立取引 [{'buyer': ..., 'seller': ..., 'price': ...}]

# タイトル
st.title("📈 経済実験：市場メカニズムと均衡価格")

# Sidebar: モード切替
mode = st.sidebar.radio("利用モードを選択", ["生徒用画面", "教員用管理画面"])

# ==========================================
# 教員用管理画面
# ==========================================
if mode == "教員用管理画面":
    st.header("⚙️ 教員用 進行・管理ダッシュボード")

    # 実験設定・開始パネル
    st.subheader("1. 実験の準備と開始")
    student_list_input = st.text_area(
        "参加する生徒の名前（または出席番号）を改行区切りで入力してください",
        "生徒1\n生徒2\n生徒3\n生徒4\n生徒5",
    )

    col1, col2 = st.columns(2)
    with col1:
        min_val = st.number_input("評価額/コストの最小値", value=100, step=50)
    with col2:
        max_val = st.number_input("評価額/コストの最大値", value=1000, step=50)

    if st.button("👥 役割割り当て＆実験スタート", type="primary"):
        students = [
            s.strip() for s in student_list_input.split("\n") if s.strip()
        ]
        num_students = len(students)

        if num_students < 2:
            st.error("生徒は2名以上必要です。")
        else:
            random.shuffle(students)

            # ルールに基づく人数調整（奇数の場合は買い手を減らす）
            half = num_students // 2
            buyers = students[:half]
            sellers = students[half:]

            players = {}
            # 買い手の設定
            for b in buyers:
                players[b] = {
                    "role": "買い手",
                    "value": random.randint(min_val // 10, max_val // 10) * 10,
                    "traded": False,
                }
            # 売り手の設定
            for s in sellers:
                players[s] = {
                    "role": "売り手",
                    "value": random.randint(min_val // 10, max_val // 10) * 10,
                    "traded": False,
                }

            st.session_state.players = players
            st.session_state.bids = []
            st.session_state.asks = []
            st.session_state.trades = []
            st.session_state.game_started = True
            st.success(
                f"実験を開始しました！（買い手: {len(buyers)}名, 売り手: {len(sellers)}名）"
            )

    st.divider()

    # リアルタイム監視パネル
    st.subheader("2. 市場の状況（リアルタイム）")

    col_a, col_b = st.columns(2)
    with col_a:
        st.write("### 📜 成約履歴")
        if st.session_state.trades:
            df_trades = pd.DataFrame(st.session_state.trades)
            st.dataframe(df_trades, use_container_width=True)
            st.line_chart(df_trades["price"])
        else:
            st.info("まだ取引は成立していません。")

    with col_b:
        st.write("### 👥 参加者一覧と割り当て条件")
        if st.session_state.players:
            df_players = pd.DataFrame.from_dict(
                st.session_state.players, orient="index"
            )
            df_players.columns = ["役割", "所持金 / コスト", "取引完了"]
            st.dataframe(df_players, use_container_width=True)

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
            "教員が実験を開始するまでお待ちください。画面を更新（F5）して確認してください。"
        )
    else:
        # 生徒の識別
        player_names = list(st.session_state.players.keys())
        my_name = st.selectbox("あなたの名前を選択してください", player_names)

        if my_name:
            my_info = st.session_state.players[my_name]
            role = my_info["role"]
            limit_val = my_info["value"]

            # 自分の状態表示
            st.info(f"**あなたの役割:** {role}")

            if role == "買い手":
                st.metric(
                    label="💰 あなたの所持金（上限価格）",
                    value=f"{limit_val} 円",
                )
                st.caption(
                    "※ これより高い金額での購入はできません。なるべく安く買いましょう。"
                )
            else:
                st.metric(
                    label="🏭 あなたの生産コスト（下限価格）",
                    value=f"{limit_val} 円",
                )
                st.caption(
                    "※ これより低い金額での売却はできません。なるべく高く売りましょう。"
                )

            if my_info["traded"]:
                st.success("🎉 あなたの取引はすでに成立しました！")
            else:
                st.divider()
                st.subheader("注文の発注")

                # 発注フォーム
                price_input = st.number_input(
                    "提示する価格（円）", min_value=0, step=10, value=limit_val
                )

                if st.button("注文を提出する", type="primary"):
                    # チェック処理
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

                        # 約定（マッチング）ロジックの実行
                        # 買いの最高値 >= 売り的最安値 であれば取引成立
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
                                # 約定価格は間を取る（または先に提示された側）
                                trade_price = (
                                    max_bid["price"] + min_ask["price"]
                                ) // 2
                                st.session_state.trades.append(
                                    {
                                        "買い手": max_bid["player"],
                                        "売り手": min_ask["player"],
                                        "price": trade_price,
                                    }
                                )
                                # フラグ更新
                                st.session_state.players[max_bid["player"]][
                                    "traded"
                                ] = True
                                st.session_state.players[min_ask["player"]][
                                    "traded"
                                ] = True
                                st.balloons()
                                st.success("取引が成立しました！")

                        st.rerun()

            # 現在の市場板情報
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