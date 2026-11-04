# Fresh-agent test of the agent guide

This tests whether `AGENT_GUIDE.md`, together with the repository, gives a new
agent what a long-serving collaborator knows. It also tests the claims ledger
behind the guide.

## Running it

1. Export the repository **without this directory**, so the agent under test
   cannot read the answers:

   ```bash
   git archive --format=tar HEAD ':!claims/guide_eval' | tar -x -C <empty-dir>
   ```

2. Start an agent with no project memory. Its brief: "Read `AGENT_GUIDE.md`,
   then answer the questions using only this repository. Cite file paths or
   claim IDs. Say 'not established' where the evidence does not settle a
   question." Give it `questions.md` from this directory, without the answer
   key.
3. Score each answer against `answers.md`: 2 = correct, with the right
   evidence; 1 = correct but unsupported or incomplete; 0 = wrong, or a trap
   was taken. Traps are marked in the key. Falling into a trap scores 0 even
   when the rest of the answer is right.
4. Record the agent, model, version, date, guide commit and score in
   `results.csv`. Each score below 2 marks a defect: fix the guide or the
   ledger, not the question.

Run it again after any substantial change to the guide or the ledger. Use a
different model family from the one that last edited the guide when one is
available.
