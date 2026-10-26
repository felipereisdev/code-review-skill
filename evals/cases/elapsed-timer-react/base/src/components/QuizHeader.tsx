interface QuizHeaderProps {
  title: string;
}

export function QuizHeader({ title }: QuizHeaderProps) {
  return (
    <header>
      <h1>{title}</h1>
    </header>
  );
}
