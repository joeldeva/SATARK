import { Suspense, lazy, useEffect } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Navigate, RouterProvider, createBrowserRouter } from 'react-router-dom';
import './i18n';
import { AppShell, RequireAuth, RoleRedirect } from './layout/AppShell';
import { refreshQueueCount, syncOfflineQueue } from './lib/apiClient';
import { useAppStore } from './store/appStore';

const LoginPage = lazy(() => import('./pages/LoginPage').then((module) => ({ default: module.LoginPage })));
const SdrdWorkspace = lazy(() => import('./pages/SdrdWorkspace').then((module) => ({ default: module.SdrdWorkspace })));
const FodWorkspace = lazy(() => import('./pages/FodWorkspace').then((module) => ({ default: module.FodWorkspace })));
const DpdWorkspace = lazy(() => import('./pages/DpdWorkspace').then((module) => ({ default: module.DpdWorkspace })));
const ScdWorkspace = lazy(() => import('./pages/ScdWorkspace').then((module) => ({ default: module.ScdWorkspace })));
const CollectionClient = lazy(() => import('./pages/CollectionClient').then((module) => ({ default: module.CollectionClient })));

function PageLoader() {
  return <div className="rounded-lg border border-slate-200 bg-white p-6 text-sm text-slate-600">Loading SATARK workspace...</div>;
}

function withSuspense(element: JSX.Element) {
  return <Suspense fallback={<PageLoader />}>{element}</Suspense>;
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false
    }
  }
});

const router = createBrowserRouter([
  { path: '/login', element: withSuspense(<LoginPage />) },
  {
    path: '/',
    element: (
      <RequireAuth>
        <AppShell />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <RoleRedirect /> },
      { path: 'sdrd', element: withSuspense(<SdrdWorkspace />) },
      { path: 'fod', element: withSuspense(<FodWorkspace />) },
      { path: 'dpd', element: withSuspense(<DpdWorkspace />) },
      { path: 'scd', element: withSuspense(<ScdWorkspace />) },
      { path: 'collect/:surveyId', element: withSuspense(<CollectionClient />) }
    ]
  },
  { path: '*', element: <Navigate to="/" replace /> }
]);

export default function App() {
  const fontScale = useAppStore((state) => state.fontScale);

  useEffect(() => {
    document.documentElement.style.setProperty('--satark-font-scale', String(fontScale));
  }, [fontScale]);

  useEffect(() => {
    void refreshQueueCount();
    const handleOnline = () => {
      void syncOfflineQueue();
    };
    window.addEventListener('online', handleOnline);
    return () => window.removeEventListener('online', handleOnline);
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
}
