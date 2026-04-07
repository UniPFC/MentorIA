import pytest
import torch
from unittest.mock import MagicMock, patch, Mock
from src.ai.provider.llm import Provider, HFProvider


@pytest.mark.unit
class TestProvider:
    @patch('src.ai.provider.llm.resolve_api_key')
    @patch('src.ai.provider.llm.OpenAI')
    def test_init_with_defaults(self, mock_openai, mock_resolve_key):
        mock_resolve_key.return_value = "test-key"
        
        provider = Provider("gpt-4")
        
        assert provider.model_name == "gpt-4"
        mock_resolve_key.assert_called_once_with("openai", None)
        mock_openai.assert_called_once()
    
    @patch('src.ai.provider.llm.resolve_api_key')
    @patch('src.ai.provider.llm.OpenAI')
    def test_init_with_custom_url(self, mock_openai, mock_resolve_key):
        mock_resolve_key.return_value = "test-key"
        
        provider = Provider(
            "custom-model",
            provider_alias="ollama",
            base_url="http://localhost:11434/v1"
        )
        
        assert provider.target_url == "http://localhost:11434/v1"
        assert provider.model_name == "custom-model"
    
    @patch('src.ai.provider.llm.resolve_api_key')
    @patch('src.ai.provider.llm.OpenAI')
    def test_generate_success(self, mock_openai, mock_resolve_key):
        mock_resolve_key.return_value = "test-key"
        
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Generated response"
        
        mock_client.chat.completions.create.return_value = mock_response
        
        provider = Provider("gpt-4")
        result = provider.generate([{"role": "user", "content": "Hello"}])
        
        assert result == "Generated response"
        mock_client.chat.completions.create.assert_called_once()
    
    @patch('src.ai.provider.llm.resolve_api_key')
    @patch('src.ai.provider.llm.OpenAI')
    def test_generate_with_params(self, mock_openai, mock_resolve_key):
        mock_resolve_key.return_value = "test-key"
        
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response"
        
        mock_client.chat.completions.create.return_value = mock_response
        
        provider = Provider("gpt-4")
        result = provider.generate(
            [{"role": "user", "content": "Hello"}],
            max_new_tokens=512,
            temperature=0.5,
            top_p=0.9
        )
        
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs['max_tokens'] == 512
        assert call_kwargs['temperature'] == 0.5
        assert call_kwargs['top_p'] == 0.9
    
    @patch('src.ai.provider.llm.resolve_api_key')
    @patch('src.ai.provider.llm.OpenAI')
    def test_generate_error_handling(self, mock_openai, mock_resolve_key):
        mock_resolve_key.return_value = "test-key"
        
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("API error")
        
        provider = Provider("gpt-4")
        
        with pytest.raises(Exception, match="API error"):
            provider.generate([{"role": "user", "content": "Hello"}])
    
    @patch('src.ai.provider.llm.resolve_api_key')
    @patch('src.ai.provider.llm.OpenAI')
    def test_generate_structured_success(self, mock_openai, mock_resolve_key):
        mock_resolve_key.return_value = "test-key"
        
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        mock_parsed = MagicMock()
        mock_message = MagicMock()
        mock_message.parsed = mock_parsed
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message = mock_message
        
        mock_client.beta.chat.completions.parse.return_value = mock_completion
        
        mock_format = MagicMock()
        mock_format.__name__ = "TestFormat"
        
        provider = Provider("gpt-4")
        result = provider.generate_structured(
            [{"role": "user", "content": "Hello"}],
            response_format=mock_format
        )
        
        assert result == mock_parsed
        mock_client.beta.chat.completions.parse.assert_called_once()
    
    @patch('src.ai.provider.llm.resolve_api_key')
    @patch('src.ai.provider.llm.OpenAI')
    def test_generate_structured_raw_content(self, mock_openai, mock_resolve_key):
        mock_resolve_key.return_value = "test-key"
        
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        mock_message = MagicMock()
        mock_message.parsed = None
        mock_message.content = "Raw content"
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message = mock_message
        
        mock_client.beta.chat.completions.parse.return_value = mock_completion
        
        mock_format = MagicMock()
        mock_format.__name__ = "TestFormat"
        
        provider = Provider("gpt-4")
        result = provider.generate_structured(
            [{"role": "user", "content": "Hello"}],
            response_format=mock_format
        )
        
        assert result == "Raw content"
    
    @patch('src.ai.provider.llm.resolve_api_key')
    @patch('src.ai.provider.llm.OpenAI')
    def test_generate_structured_error(self, mock_openai, mock_resolve_key):
        mock_resolve_key.return_value = "test-key"
        
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.beta.chat.completions.parse.side_effect = Exception("Parse error")
        
        mock_format = MagicMock()
        mock_format.__name__ = "TestFormat"
        
        provider = Provider("gpt-4")
        
        with pytest.raises(Exception, match="Parse error"):
            provider.generate_structured(
                [{"role": "user", "content": "Hello"}],
                response_format=mock_format
            )
    
    @patch('src.ai.provider.llm.resolve_api_key')
    @patch('src.ai.provider.llm.OpenAI')
    def test_generate_stream_success(self, mock_openai, mock_resolve_key):
        mock_resolve_key.return_value = "test-key"
        
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [MagicMock()]
        mock_chunk1.choices[0].delta.content = "Hello "
        
        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [MagicMock()]
        mock_chunk2.choices[0].delta.content = "world"
        
        mock_chunk3 = MagicMock()
        mock_chunk3.choices = [MagicMock()]
        mock_chunk3.choices[0].delta.content = None
        
        mock_client.chat.completions.create.return_value = iter([mock_chunk1, mock_chunk2, mock_chunk3])
        
        provider = Provider("gpt-4")
        chunks = list(provider.generate_stream([{"role": "user", "content": "Hello"}]))
        
        assert len(chunks) == 2
        assert chunks[0] == "Hello "
        assert chunks[1] == "world"
    
    @patch('src.ai.provider.llm.resolve_api_key')
    @patch('src.ai.provider.llm.OpenAI')
    def test_generate_stream_error(self, mock_openai, mock_resolve_key):
        mock_resolve_key.return_value = "test-key"
        
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("Stream error")
        
        provider = Provider("gpt-4")
        
        with pytest.raises(Exception, match="Stream error"):
            list(provider.generate_stream([{"role": "user", "content": "Hello"}]))


@pytest.mark.unit
class TestHFProvider:
    def test_init(self):
        mock_model = MagicMock()
        mock_model.generation_config = MagicMock()
        mock_tokenizer = MagicMock()
        
        provider = HFProvider(mock_model, mock_tokenizer)
        
        assert provider.model == mock_model
        assert provider.tokenizer == mock_tokenizer
        mock_model.eval.assert_called_once()
        assert mock_model.generation_config.temperature is None
    
    def test_init_no_generation_config(self):
        mock_model = MagicMock()
        del mock_model.generation_config
        mock_tokenizer = MagicMock()
        
        provider = HFProvider(mock_model, mock_tokenizer)
        
        assert provider.model == mock_model
        assert provider.tokenizer == mock_tokenizer
    
    def test_generate_success(self):
        mock_model = MagicMock()
        mock_model.device = 'cpu'
        mock_tokenizer = MagicMock()
        mock_tokenizer.pad_token_id = 0
        
        input_ids = torch.tensor([[1, 2, 3]])
        mock_tokenizer.apply_chat_template.return_value.to.return_value = input_ids
        
        output_ids = torch.tensor([[1, 2, 3, 4, 5, 6]])
        mock_model.generate.return_value = output_ids
        
        mock_tokenizer.decode.return_value = "Generated response"
        
        provider = HFProvider(mock_model, mock_tokenizer)
        result = provider.generate([{"role": "user", "content": "Hello"}])
        
        assert result == "Generated response"
        mock_tokenizer.apply_chat_template.assert_called_once()
        mock_model.generate.assert_called_once()
    
    def test_generate_with_params(self):
        mock_model = MagicMock()
        mock_model.device = 'cpu'
        mock_tokenizer = MagicMock()
        mock_tokenizer.pad_token_id = 0
        
        input_ids = torch.tensor([[1, 2, 3]])
        mock_tokenizer.apply_chat_template.return_value.to.return_value = input_ids
        
        output_ids = torch.tensor([[1, 2, 3, 4, 5]])
        mock_model.generate.return_value = output_ids
        
        mock_tokenizer.decode.return_value = "Response"
        
        provider = HFProvider(mock_model, mock_tokenizer)
        result = provider.generate(
            [{"role": "user", "content": "Hello"}],
            max_new_tokens=512,
            temperature=0.5,
            top_p=0.9
        )
        
        call_kwargs = mock_model.generate.call_args[1]
        assert call_kwargs['max_new_tokens'] == 512
        assert call_kwargs['top_p'] == 0.9
        assert 'temperature' not in call_kwargs
    
    def test_generate_template_error(self):
        mock_model = MagicMock()
        mock_tokenizer = MagicMock()
        mock_tokenizer.apply_chat_template.side_effect = Exception("Template error")
        
        provider = HFProvider(mock_model, mock_tokenizer)
        
        with pytest.raises(Exception, match="Template error"):
            provider.generate([{"role": "user", "content": "Hello"}])
