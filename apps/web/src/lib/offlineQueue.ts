import { openDB, type DBSchema } from 'idb';

interface SatarkQueueDb extends DBSchema {
  requests: {
    key: number;
    value: {
      id?: number;
      url: string;
      method: string;
      body?: unknown;
      createdAt: string;
    };
  };
}

const dbPromise = openDB<SatarkQueueDb>('satark-offline-queue', 1, {
  upgrade(db) {
    if (!db.objectStoreNames.contains('requests')) {
      db.createObjectStore('requests', { keyPath: 'id', autoIncrement: true });
    }
  }
});

export async function queueRequest(url: string, method: string, body?: unknown) {
  const db = await dbPromise;
  await db.add('requests', {
    url,
    method,
    body,
    createdAt: new Date().toISOString()
  });
  return getQueuedCount();
}

export async function getQueuedCount() {
  const db = await dbPromise;
  return db.count('requests');
}

export async function syncQueue(apiBase: string) {
  const db = await dbPromise;
  const requests = await db.getAll('requests');
  for (const request of requests) {
    const response = await fetch(`${apiBase}${request.url}`, {
      method: request.method,
      headers: { 'Content-Type': 'application/json' },
      body: request.body ? JSON.stringify(request.body) : undefined
    });
    if (response.ok && request.id) {
      await db.delete('requests', request.id);
    }
  }
  return getQueuedCount();
}
