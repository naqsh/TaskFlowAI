1) Read the request context (user_id, workspace_id, nl_input).
2) Fetch up to N relevant tasks/projects/comments using allowed tools.
3) Wrap all external strings with the spotlighting markers.
4) Return strict JSON containing tasks/projects/comments and a short context_summary.

