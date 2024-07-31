import requests
import streamlit as st
import json
import yfinance as yf
import pandas as pd
import numpy as np
import subprocess

class CompletionExecutor:
    def __init__(self, host, api_key, api_key_primary_val, request_id):
        self._host = host
        self._api_key = api_key
        self._api_key_primary_val = api_key_primary_val
        self._request_id = request_id

    def execute(self, completion_request):
        headers = {
            'X-NCP-CLOVASTUDIO-API-KEY': self._api_key,
            'X-NCP-APIGW-API-KEY': self._api_key_primary_val,
            'X-NCP-CLOVASTUDIO-REQUEST-ID': self._request_id,
            'Content-Type': 'application/json; charset=utf-8',
            'Accept': 'text/event-stream'
        }

        response_text = ""
        with requests.post(self._host + '/testapp/v1/chat-completions/HCX-DASH-001',
                           headers=headers, json=completion_request, stream=True) as r:
            for line in r.iter_lines():
                if line:
                    decoded_line = line.decode("utf-8")
                    if decoded_line.startswith("data:"):
                        data_str = decoded_line[len("data:"):].strip()
                        if data_str:
                            data_json = json.loads(data_str)
                            if 'message' in data_json and 'content' in data_json['message']:
                                response_text += data_json['message']['content']
        return response_text

def parse_code(response_text):
    start_token = "```python"
    end_token = "```"
    start_index = response_text.find(start_token)
    end_index = response_text.find(end_token, start_index + len(start_token))
    if start_index != -1 and end_index != -1:
        code = response_text[start_index + len(start_token):end_index].strip()
        return code
    return None

def save_code_to_file(code, filename="backtest.py"):
    with open(filename, "w") as file:
        file.write(code)

def execute_code(filename="backtest.py"):
    # Debugging print statements
    print(f"Executing code in file: {filename}")
    try:
        result = subprocess.run(['python', filename], capture_output=True, text=True)
        # Print the results for debugging purposes
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")
        return result.stdout, result.stderr
    except Exception as e:
        print(f"An error occurred: {e}")
        return "", str(e)

def main():
    st.title("Investment Strategy Backtesting Chatbot")

    host = 'https://clovastudio.stream.ntruss.com'
    api_key = 'NTA0MjU2MWZlZTcxNDJiY+/olPT0j779Mhyhv4LcWFkTSyrYPXdze6FTxYiwpZ6C'
    api_key_primary_val = 'KD3NXRvOwDqVKeiMGvWQGlykzlF159C6rKueyocL'
    request_id = 'bbf6078f-2821-4eee-8e8c-15759a24df03'

    completion_executor = CompletionExecutor(host, api_key, api_key_primary_val, request_id)

    if 'messages' not in st.session_state:
        st.session_state['messages'] = []

    ticker = st.text_input("Enter the ticker (e.g., 005930.KS, AAPL): ", key="ticker")
    start_date = st.text_input("Enter the start date (YYYY-MM-DD): ", key="start_date")
    end_date = st.text_input("Enter the end date (YYYY-MM-DD): ", key="end_date")
    strategy = st.text_input("Describe your investment strategy: ", key="strategy")

    if st.button("Submit"):
        if ticker and start_date and end_date and strategy:
            user_input = f"Ticker: {ticker}, Start Date: {start_date}, End Date: {end_date}, Strategy: {strategy}"
            st.session_state.messages.append({"role": "user", "content": user_input})

            request_data_for_code = {
                'messages': st.session_state.messages + [{"role": "assistant", "content": "주어진 티커, 시작 날짜, 종료 날짜를 사용하여 yfinance를 이용한 백테스팅을 수행하는 코드를 작성하세요. 백테스팅 결과에는 누적 로그 수익률, 최대 낙폭(MDD), 샤프 비율 계산이 포함되어야 합니다."}],
                'topP': 0.8,
                'topK': 0,
                'maxTokens': 1024,
                'temperature': 0.1,
                'repeatPenalty': 5.0,
                'stopBefore': [],
                'includeAiFilters': True,
                'seed': 0
            }

            generated_code_response = completion_executor.execute(request_data_for_code)
            generated_code = parse_code(generated_code_response)

            if generated_code:
                save_code_to_file(generated_code)
                execution_result, execution_error = execute_code()
                
                if execution_error:
                    st.session_state.messages.append({"role": "assistant", "content": f"Execution error:\n{execution_error}"})
                else:
                    st.session_state.messages.append({"role": "assistant", "content": f"Generated code:\n```python\n{generated_code}\n```"})
                    st.session_state.messages.append({"role": "assistant", "content": f"Execution result:\n{execution_result}"})

                    request_data_for_interpretation = {
                        'messages': st.session_state.messages + [{"role": "assistant", "content": f"다음 실행결과를 기반으로 해석해줘:\n{execution_result}"}],
                        'topP': 0.8,
                        'topK': 0,
                        'maxTokens': 1024,
                        'temperature': 0.5,
                        'repeatPenalty': 5.0,
                        'stopBefore': [],
                        'includeAiFilters': True,
                        'seed': 0
                    }

                    feedback = completion_executor.execute(request_data_for_interpretation)
                    st.session_state.messages.append({"role": "assistant", "content": feedback})
            else:
                st.session_state.messages.append({"role": "assistant", "content": "Failed to generate code."})
            st.experimental_rerun()

    for i, message_dict in enumerate(st.session_state['messages']):
        if message_dict["role"] == "user":
            st.markdown(f"**User:** {message_dict['content']}")
        elif message_dict["role"] == "assistant":
            st.markdown(f"**Assistant:** {message_dict['content']}")

if __name__ == "__main__":
    main()
