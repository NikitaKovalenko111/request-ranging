export function mockDelay<T>(value: T, signal?: AbortSignal, delay = 280): Promise<T> {
  return new Promise((resolve, reject) => {
    const timer = window.setTimeout(() => resolve(structuredClone(value)), delay);
    signal?.addEventListener('abort', () => {
      window.clearTimeout(timer);
      reject(new DOMException('Запрос отменён', 'AbortError'));
    }, { once: true });
  });
}

