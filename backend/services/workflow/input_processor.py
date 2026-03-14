class InputProcessor:
    @staticmethod
    def build_enhanced_input(user_input: str) -> str:
        """
        保持用户输入的纯粹性。
        不再这里注入 JSON，JSON 已经通过 context 字段独立传输了。
        """
        return user_input.strip()