import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertTriangle } from 'lucide-react';

interface Props { children: ReactNode; resetKey: string }
interface State { error: Error | null }

export class PageErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State { return { error }; }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Page render error', error, info.componentStack);
  }

  componentDidUpdate(previous: Props) {
    if (previous.resetKey !== this.props.resetKey && this.state.error) this.setState({ error: null });
  }

  render() {
    if (!this.state.error) return this.props.children;
    return <section className="state-view panel error-state"><AlertTriangle /><h2>Страница завершилась с ошибкой</h2><p>Оболочка приложения продолжает работать. Перезагрузите только текущий экран.</p><button className="button secondary" onClick={() => this.setState({ error: null })}>Повторить отображение</button></section>;
  }
}
