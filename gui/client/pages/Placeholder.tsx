import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Brain, Database, Settings, Network, BookOpen } from 'lucide-react';

interface PlaceholderProps {
  title: string;
}

const Placeholder: React.FC<PlaceholderProps> = ({ title }) => {
  const getIcon = () => {
    switch (title) {
      case 'Models':
        return <Brain className="h-8 w-8 text-blue-600" />;
      case 'Collections':
        return <Database className="h-8 w-8 text-green-600" />;
      case 'Connections':
        return <Network className="h-8 w-8 text-purple-600" />;
      case 'Settings':
        return <Settings className="h-8 w-8 text-gray-600" />;
      default:
        return <BookOpen className="h-8 w-8 text-blue-600" />;
    }
  };

  const getDescription = () => {
    switch (title) {
      case 'Models':
        return 'Configure and manage AI models for knowledge processing';
      case 'Collections':
        return 'Browse and manage ChromaDB collections';
      case 'Connections':
        return 'Monitor system connections and integrations';
      case 'Settings':
        return 'Configure system settings and preferences';
      default:
        return 'Coming soon...';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-6">
      <div className="max-w-4xl mx-auto">
        <Card className="text-center">
          <CardHeader>
            <div className="mx-auto w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mb-4">
              {getIcon()}
            </div>
            <CardTitle className="text-3xl">{title}</CardTitle>
            <CardDescription className="text-lg">
              {getDescription()}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="bg-blue-50 p-6 rounded-lg">
              <h3 className="font-semibold text-blue-900 mb-2">🚧 Under Development</h3>
              <p className="text-blue-700">
                This section is currently being developed and will be available soon.
                Check back later for updates!
              </p>
            </div>

            <div className="flex gap-2 justify-center">
              <Button variant="outline" onClick={() => window.history.back()}>
                Go Back
              </Button>
              <Button onClick={() => window.location.href = '/'}>
                Go Home
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Placeholder;
