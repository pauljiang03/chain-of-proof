# Question-driven comparison input

Investigate the supplied NIST Data Leakage Case evidence and answer the questions in `questions.json`. This list is a new question-only projection prepared for comparison. It is not the original published Mulder investigation prompt.

For each answer, cite its source evidence and state the time zone and timestamp meaning when relevant. Distinguish direct observations from inferences. Use `unknown` when the evidence does not support an answer, and `unanswered` when the question was not investigated. Do not infer that an application performed an action only because it was installed or launched. Do not infer a negative conclusion only because a parser found no records.

An answer can be prose or structured content in the `answer` field. The `evidence` list should identify artifacts, records, offsets or source locations. Put inferential claims and their basis in `inferences`. A proof-producing system may attach certificate identifiers and specify exactly which fields each certificate supports. Evidence metadata is not automatically a formally proved answer.

Submit the complete report as well as any structured answers. Record the system, run ID, report path, and report SHA-256. The response template supplies question IDs but no expected facts.

Do not read the evaluator-only directory, answer key, reference answers, or historical assessment reports. The comparison coordinator must keep those files outside the investigator's accessible inputs.
