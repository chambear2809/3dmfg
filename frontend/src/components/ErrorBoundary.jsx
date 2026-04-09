import React from "react";

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null, info: null, key: 0 };
  }
  static getDerivedStateFromError(error) {
    return { error };
  }
  componentDidCatch(error, info) {
    this.setState({ info });
    if (this.props.onError) this.props.onError(error, info);
     
    console.error("ErrorBoundary", error, info);
  }
  handleRetry = () =>
    this.setState({ error: null, info: null, key: this.state.key + 1 });

  render() {
    if (this.state.error) {
      return (
        <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: 'var(--bg-primary)' }}>
          <div className="border rounded-xl p-6 max-w-lg w-full" style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-subtle)' }}>
            <div className="text-red-300 font-semibold mb-2">Something broke</div>
            <div className="text-sm mb-4" style={{ color: 'var(--text-secondary)' }}>
              The UI hit an unexpected error. You can try again.
            </div>
            <div className="flex gap-2">
              <button
                onClick={this.handleRetry}
                className="px-3 py-2 text-white rounded-lg text-sm transition-all hover:shadow-glow"
                style={{ backgroundColor: 'var(--primary)' }}
              >
                Retry
              </button>
              <button
                onClick={() => {
                  const msg = `${this.state.error?.stack || this.state.error?.message || String(this.state.error)}\n\n${
                    this.state.info?.componentStack || ""
                  }`;
                  navigator.clipboard?.writeText(msg).catch(() => {});
                }}
                className="px-3 py-2 text-white rounded-lg text-sm transition-colors"
                style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)' }}
              >
                Copy details
              </button>
            </div>
            <pre className="text-xs mt-4 max-h-48 overflow-auto whitespace-pre-wrap" style={{ color: 'var(--text-muted)' }}>
              {this.state.error?.message}
            </pre>
          </div>
        </div>
      );
    }
    return (
      <React.Fragment key={this.state.key}>{this.props.children}</React.Fragment>
    );
  }
}
