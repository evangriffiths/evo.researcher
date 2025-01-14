import pytest
import tempfile

import evo_researcher.benchmark.benchmark as bm
from evo_researcher.benchmark.agents import parse_prediction_str


@pytest.fixture
def dummy_agent():
    class DummyAgent(bm.AbstractBenchmarkedAgent):
        def __init__(self):
            super().__init__(agent_name="dummy")

        def research_and_predict(self, market_question: str) -> bm.Prediction:
            return bm.Prediction(p_yes=0.6, confidence=0.8, info_utility=0.9)

    return DummyAgent()


def test_agent_prediction(dummy_agent):
    prediction = dummy_agent.research_and_predict(market_question="Will GNO go up?")
    assert prediction.p_yes == 0.6
    assert prediction.confidence == 0.8
    assert prediction.info_utility == 0.9


def test_benchmark_run(dummy_agent):
    benchmarker = bm.Benchmarker(
        markets=bm.get_markets(number=1, source=bm.MarketSource.MANIFOLD),
        agents=[dummy_agent],
    )
    benchmarker.run_agents()
    benchmarker.generate_markdown_report()


def test_parse_result_str_to_json():
    prediction = (
        "```json\n"
        "{\n"
        '  "p_yes": 0.6,\n'
        '  "p_no": 0.4,\n'
        '  "confidence": 0.8,\n'
        '  "info_utility": 0.9\n'
        "}\n"
        "```\n"
    )
    prediction: bm.Prediction = parse_prediction_str(prediction)
    assert prediction.p_yes == 0.6
    assert prediction.confidence == 0.8
    assert prediction.info_utility == 0.9


def test_cache():
    cache = bm.PredictionsCache(
        predictions={
            "bar": {"foo": bm.Prediction(p_yes=0.6, confidence=0.8, info_utility=0.9)}
        }
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = f"{tmpdir}/cache.json"
        cache.save(cache_path)

        cache_loaded = bm.PredictionsCache.parse_file(cache_path)
        assert cache == cache_loaded


def test_benchmarker_cache(dummy_agent):
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = f"{tmpdir}/cache.json"
        markets = bm.get_markets(number=1, source=bm.MarketSource.MANIFOLD)
        benchmarker = bm.Benchmarker(
            markets=markets,
            agents=[dummy_agent],
            cache_path=cache_path,
        )
        prediction = bm.Prediction(
            p_yes=0.00001, confidence=0.22222, info_utility=0.3333
        )
        benchmarker.add_prediction(
            agent=dummy_agent,
            prediction=prediction,
            market_question=markets[0].question,
        )
        assert (
            benchmarker.get_prediction(
                agent_name=dummy_agent.agent_name, question=markets[0].question
            ).p_yes
            == prediction.p_yes
        )
        benchmarker.predictions.save(cache_path)

        another_benchmarker = bm.Benchmarker(
            markets=markets,
            agents=[dummy_agent],
            cache_path=cache_path,
        )
        assert (
            another_benchmarker.get_prediction(
                agent_name=dummy_agent.agent_name, question=markets[0].question
            ).p_yes
            == prediction.p_yes
        )
        another_benchmarker.run_agents()

        # Observe that the cached result is still the same
        assert (
            another_benchmarker.get_prediction(
                agent_name=dummy_agent.agent_name, question=markets[0].question
            ).p_yes
            == prediction.p_yes
        )
