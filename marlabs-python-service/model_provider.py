class ModelProvider:

    def generate_answer(self, question: str, context: str) -> str:
        """
        Simple deterministic answer provider.

        A real LLM can be integrated later.
        """

        if not context:
            return "INSUFFICIENT_EVIDENCE"

        return f"Based on the available policy evidence: {context}"
