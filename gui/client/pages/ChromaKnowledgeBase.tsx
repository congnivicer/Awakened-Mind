import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Search, Database, Brain, Zap, Activity, BookOpen, Github } from 'lucide-react';

interface KnowledgeItem {
  id: string;
  document: string;
  distance: number;
  metadata: {
    title?: string;
    source?: string;
    timestamp?: string;
    [key: string]: any;
  };
}

interface Collection {
  name: string;
  count: number;
}

interface SystemStatus {
  status: string;
  timestamp: string;
  components: {
    [key: string]: {
      status: string;
    };
  };
  metrics: {
    knowledge_items: number;
    active_operations: number;
    initialized: boolean;
  };
}

const ChromaKnowledgeBase: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<KnowledgeItem[]>([]);
  const [collections, setCollections] = useState<Collection[]>([]);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [isHarvesting, setIsHarvesting] = useState(false);
  const [selectedCollection, setSelectedCollection] = useState('technical_docs');

  // Fetch system status on component mount
  useEffect(() => {
    fetchSystemStatus();
    fetchCollections();
  }, []);

  const fetchSystemStatus = async () => {
    try {
      // Fetch collections to get real knowledge count
      const collectionsResponse = await fetch('http://localhost:3001/api/collections');
      let totalKnowledgeItems = 0;

      if (collectionsResponse.ok) {
        const collectionsData = await collectionsResponse.json();
        const collections = collectionsData.collections || [];
        totalKnowledgeItems = collections.reduce((sum, collection) => sum + (collection.count || 0), 0);

        // Update collections state
        setCollections(collections);
        setSelectedCollection(collections.length > 0 ? collections[0].name : 'technical_docs');
      }

      // Fetch health status
      const healthResponse = await fetch('http://localhost:3001/api/health');
      if (healthResponse.ok) {
        const healthData = await healthResponse.json();

        setSystemStatus({
          status: 'healthy',
          timestamp: new Date().toISOString(),
          components: {
            knowledge_system: { status: 'ready' },
            github_discoverer: { status: 'ready' },
            processing_pipeline: { status: 'ready' }
          },
          metrics: {
            knowledge_items: totalKnowledgeItems,
            active_operations: isHarvesting ? 1 : 0,
            initialized: true
          }
        });
      }
    } catch (error) {
      console.error('Failed to fetch system status:', error);
      // Set fallback status
      setSystemStatus({
        status: 'unknown',
        timestamp: new Date().toISOString(),
        components: {},
        metrics: {
          knowledge_items: 0,
          active_operations: 0,
          initialized: false
        }
      });
    }
  };

  const fetchCollections = async () => {
    // Collections are already fetched in fetchSystemStatus
    // This function is kept for manual refresh if needed
    try {
      const response = await fetch('http://localhost:3001/api/collections');
      if (response.ok) {
        const data = await response.json();
        setCollections(data.collections || []);
      }
    } catch (error) {
      console.error('Failed to fetch collections:', error);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;

    setIsSearching(true);
    try {
      const response = await fetch('http://localhost:3001/api/knowledge/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: searchQuery,
          collection: selectedCollection,
          limit: 20,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        const results = data.results || [];
        setSearchResults(results);

        if (results.length === 0) {
          alert(`🔍 No results found for "${searchQuery}" in ${selectedCollection}`);
        } else {
          alert(`✅ Found ${results.length} results for "${searchQuery}"`);
        }
      } else {
        console.error('Search failed:', response.statusText);
        setSearchResults([]);
        alert('❌ Search failed. Please check the console for details.');
      }
    } catch (error) {
      console.error('Search error:', error);
      setSearchResults([]);
      alert('❌ Search error. Please check the console for details.');
    } finally {
      setIsSearching(false);
    }
  };

  const handleHarvest = async () => {
    setIsHarvesting(true);
    try {
      const response = await fetch('http://localhost:3001/api/knowledge/harvest', {
        method: 'POST',
      });

      if (response.ok) {
        const result = await response.json();
        console.log('Harvest result:', result);

        // Update system status with new data
        if (result.summary) {
          setSystemStatus(prev => ({
            ...prev,
            status: 'healthy',
            timestamp: result.timestamp,
            metrics: {
              knowledge_items: result.summary.total_knowledge_items || prev?.metrics?.knowledge_items || 0,
              active_operations: 0,
              initialized: true
            }
          }));
        }

        // Refresh collections after harvest
        setTimeout(() => {
          fetchCollections();
        }, 1000); // Small delay to allow backend to process

        alert(`✅ Harvest completed successfully!\n\n📊 Summary:\n• ${result.summary?.repositories_discovered || 0} repositories discovered\n• ${result.summary?.documents_extracted || 0} documents extracted\n• ${result.summary?.documents_stored || 0} documents stored\n• Total knowledge items: ${result.summary?.total_knowledge_items || 0}`);
      } else {
        console.error('Harvest failed:', response.statusText);
        alert('❌ Harvest failed. Please check the console for details.');
      }
    } catch (error) {
      console.error('Harvest error:', error);
      alert('❌ Harvest error. Please check the console for details.');
    } finally {
      setIsHarvesting(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ready': return 'bg-green-500';
      case 'not_initialized': return 'bg-yellow-500';
      default: return 'bg-gray-500';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <h1 className="text-4xl font-bold text-slate-900 flex items-center justify-center gap-3">
            <Brain className="h-10 w-10 text-blue-600" />
            Awakened Mind
          </h1>
          <p className="text-lg text-slate-600">
            Knowledge Harvesting & Intelligence System
          </p>
        </div>

        {/* System Status Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">System Status</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                <span className={`inline-block w-3 h-3 rounded-full mr-2 ${systemStatus?.status === 'healthy' ? 'bg-green-500' : 'bg-red-500'}`}></span>
                {systemStatus?.status || 'Unknown'}
              </div>
              <p className="text-xs text-muted-foreground">
                Last updated: {systemStatus?.timestamp ? new Date(systemStatus.timestamp).toLocaleTimeString() : 'Never'}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Knowledge Items</CardTitle>
              <Database className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{systemStatus?.metrics?.knowledge_items || 0}</div>
              <p className="text-xs text-muted-foreground">
                Across all collections
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Active Operations</CardTitle>
              <Zap className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{systemStatus?.metrics?.active_operations || 0}</div>
              <p className="text-xs text-muted-foreground">
                Currently running
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Collections</CardTitle>
              <BookOpen className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{collections.length}</div>
              <p className="text-xs text-muted-foreground">
                ChromaDB collections
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Main Content Tabs */}
        <Tabs defaultValue="search" className="space-y-4">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="search">Search Knowledge</TabsTrigger>
            <TabsTrigger value="collections">Collections</TabsTrigger>
            <TabsTrigger value="harvest">Harvest</TabsTrigger>
            <TabsTrigger value="status">System Status</TabsTrigger>
          </TabsList>

          {/* Search Tab */}
          <TabsContent value="search" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Search className="h-5 w-5" />
                  Knowledge Search
                </CardTitle>
                <CardDescription>
                  Search through your knowledge base using natural language queries
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex gap-2">
                  <Input
                    placeholder="Enter your search query..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                    className="flex-1"
                  />
                  <Button onClick={handleSearch} disabled={isSearching}>
                    {isSearching ? 'Searching...' : 'Search'}
                  </Button>
                </div>

                <div className="flex gap-2">
                  <label className="text-sm font-medium">Collection:</label>
                  <select
                    value={selectedCollection}
                    onChange={(e) => setSelectedCollection(e.target.value)}
                    className="px-3 py-1 border rounded-md text-sm"
                  >
                    {collections.map((collection) => (
                      <option key={collection.name} value={collection.name}>
                        {collection.name} ({collection.count} items)
                      </option>
                    ))}
                  </select>
                </div>

                {searchResults.length > 0 && (
                  <ScrollArea className="h-96 w-full border rounded-md p-4">
                    <div className="space-y-4">
                      {searchResults.map((result, index) => (
                        <Card key={result.id || index} className="p-4">
                          <div className="space-y-2">
                            <div className="flex items-start justify-between">
                              <h3 className="font-semibold text-sm">
                                {result.metadata?.title || `Result ${index + 1}`}
                              </h3>
                              <Badge variant="outline">
                                Score: {(1 - result.distance).toFixed(3)}
                              </Badge>
                            </div>
                            <p className="text-sm text-gray-600 line-clamp-3">
                              {result.document}
                            </p>
                            {result.metadata?.source && (
                              <Badge variant="secondary" className="text-xs">
                                {result.metadata.source}
                              </Badge>
                            )}
                          </div>
                        </Card>
                      ))}
                    </div>
                  </ScrollArea>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Collections Tab */}
          <TabsContent value="collections" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Database className="h-5 w-5" />
                  ChromaDB Collections
                </CardTitle>
                <CardDescription>
                  Overview of all knowledge collections and their contents
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {collections.map((collection) => (
                    <Card key={collection.name} className="p-4">
                      <div className="space-y-2">
                        <h3 className="font-semibold">{collection.name}</h3>
                        <p className="text-2xl font-bold text-blue-600">{collection.count}</p>
                        <p className="text-sm text-gray-500">documents</p>
                      </div>
                    </Card>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Harvest Tab */}
          <TabsContent value="harvest" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Github className="h-5 w-5" />
                  Knowledge Harvesting
                </CardTitle>
                <CardDescription>
                  Discover and harvest knowledge from GitHub repositories
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="bg-blue-50 p-4 rounded-lg">
                  <h3 className="font-semibold text-blue-900 mb-2">Automated Discovery</h3>
                  <p className="text-sm text-blue-700 mb-4">
                    The system will automatically discover relevant GitHub repositories and extract their knowledge content.
                  </p>
                </div>

                <Button
                  onClick={handleHarvest}
                  disabled={isHarvesting}
                  className="w-full"
                  size="lg"
                >
                  {isHarvesting ? 'Harvesting Knowledge...' : 'Start Knowledge Harvest'}
                </Button>
              </CardContent>
            </Card>
          </TabsContent>

          {/* System Status Tab */}
          <TabsContent value="status" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="h-5 w-5" />
                  System Components
                </CardTitle>
                <CardDescription>
                  Detailed status of all system components
                </CardDescription>
              </CardHeader>
              <CardContent>
                {systemStatus?.components && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {Object.entries(systemStatus.components).map(([component, info]) => (
                      <div key={component} className="flex items-center justify-between p-3 border rounded-lg">
                        <span className="font-medium capitalize">{component.replace('_', ' ')}</span>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${info.status === 'ready' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                          }`}>
                          {info.status}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default ChromaKnowledgeBase;
