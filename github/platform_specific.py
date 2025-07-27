from typing import List, Dict, Optional

class PlatformSpecific:
    def __init__(self):
        pass

    def _extract_and_analyze_issue_comments(self, issue, top_n: int = 10) -> List[Dict]:
        """
        Extract and analyze comments for relevance from a GitHub Issue/PR.
        Limits the output to the top_n most relevant comments.
        """
        all_relevant_comments_with_scores = []
        try:
            for comment in issue.get_comments():
                comment_text = comment.body
                if comment_text:
                    is_comment_relevant, relevance_score, new_keywords = self._analyze_text_relevance(comment_text, self.global_keywords)
                    # print(f"  Comment Relevance Score: {relevance_score:.4f} (Threshold: 0.35)") # Moved this print to _process_comment for consistency
                    
                    if is_comment_relevant:
                        # Store comment data along with its score
                        comment_data = {
                            'id': comment.id,
                            'author': str(comment.user.login) if comment.user else "N/A",
                            'text': comment_text,
                            'relevance_score': relevance_score,
                            'replies': [] # GitHub comments are not nested
                        }
                        all_relevant_comments_with_scores.append((relevance_score, comment_data, new_keywords))
                        # Update global keywords immediately when a relevant comment is found
                        self._update_global_keywords(new_keywords)

        except Exception as e:
            print(f"Error extracting comments for item {issue.id}: {e}")
        
        # Sort by relevance score in descending order
        all_relevant_comments_with_scores.sort(key=lambda x: x[0], reverse=True)
        
        # Select top N comments
        top_n_comments_data = [comment_tuple[1] for comment_tuple in all_relevant_comments_with_scores[:top_n]]
        
        # This print statement should happen for each individual comment analysis, not here for the list
        # For overall summary, we can print how many top comments were selected.
        print(f"  Selected top {len(top_n_comments_data)} relevant comments.")

        return top_n_comments_data
    
    def _extract_issue_data(self, item) -> Dict:
        """Extract relevant data from a PyGithub Issue or Pull Request object."""
        # Safely get reaction_score
        reaction_score = 0
        if hasattr(item, 'reactions') and item.reactions is not None:
            if hasattr(item.reactions, 'total_count'):
                reaction_score = item.reactions.total_count
            else:
                try:
                    reaction_score = item.reactions.get('total_count', 0)
                except AttributeError:
                    reaction_score = 0

        return {
            'id': item.id,
            'url': item.html_url,
            'title': item.title,
            'content': item.body,
            'author': str(item.user.login) if item.user else "N/A",
            'date': item.created_at.isoformat(),
            'reaction_score': reaction_score, 
            'comments_count': item.comments 
        }
    
    def _process_comment(self, comment) -> Optional[Dict]:
        """
        Process a single GitHub comment.
        This function is now primarily for analyzing and extracting data,
        with the filtering/limiting done by _extract_and_analyze_issue_comments.
        """
        # The core logic for relevance analysis and keyword extraction for a single comment
        # is performed here. The decision to include it in the final list and limit the number
        # is handled by the calling function.
        relevant_comment_data = None
        comment_text = comment.body
        if comment_text:
            is_comment_relevant, relevance_score, new_keywords = self._analyze_text_relevance(comment_text, self.global_keywords)
            print(f"  Comment Relevance Score: {relevance_score:.4f} (Threshold: 0.4)")

            if is_comment_relevant:
                relevant_comment_data = {
                    'id': comment.id,
                    'author': str(comment.user.login) if comment.user else "N/A",
                    'text': comment_text,
                    'relevance_score': relevance_score,
                    'replies': [] # GitHub comments are not nested
                }
                # Note: Keyword updating for comments is now done in _extract_and_analyze_issue_comments
                # to ensure keywords are updated even if the comment isn't in the top N final list.
                # However, to be consistent with previous runs that updated global keywords on ANY relevant comment,
                # I'll keep the _update_global_keywords call here. If performance is an issue or
                # a stricter definition of "global" keywords is desired (only from top N comments),
                # this could be moved. For now, maintaining prior behavior of updating keywords for any relevant comment.
                self._update_global_keywords(new_keywords)
                
        return relevant_comment_data