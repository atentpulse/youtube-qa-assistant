import { apiClient } from './client';

export function askQuestion(
  {
    video_id,
    question,
    conversation_id,
    answer_length,
    response_style,
    prefer_structured,
    include_examples,
  },
  opts
) {
  return apiClient.post(
    '/ask',
    {
      video_id,
      question,
      conversation_id,
      answer_length,
      response_style,
      prefer_structured,
      include_examples,
    },
    opts
  );
}
