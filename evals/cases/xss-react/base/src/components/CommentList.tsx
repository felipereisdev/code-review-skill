type Comment = { id: number; author: string; body: string };

export function CommentList({ comments }: { comments: Comment[] }) {
  return (
    <ul>
      {comments.map((comment) => (
        <li key={comment.id}>
          <strong>{comment.author}</strong>
        </li>
      ))}
    </ul>
  );
}
