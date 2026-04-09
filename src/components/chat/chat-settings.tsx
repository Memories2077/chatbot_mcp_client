"use client";

import * as React from 'react';
import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

import { Button } from '@/components/ui/button';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
  SheetFooter,
} from '@/components/ui/sheet';
import { Icons } from '@/components/icons';
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import type { ChatSettings } from '@/lib/types';
import { Separator } from '../ui/separator';
import { MODEL_CONFIG } from '@/lib/config';

interface ChatSettingsProps {
  settings: ChatSettings;
  setSettings: (settings: Partial<ChatSettings>) => void;
}

const settingsSchema = z.object({
  provider: z.enum(['gemini', 'groq', 'metaclaw']),
  model: z.string(),
  temperature: z.number().min(0).max(1),
  maxTokens: z.number().min(1),
  mcpServers: z.array(z.object({ url: z.string().url('Please enter a valid URL.') })),
});

export function ChatSettings({ settings, setSettings }: ChatSettingsProps) {
  const [isOpen, setIsOpen] = React.useState(false);

  const form = useForm<ChatSettings>({
    resolver: zodResolver(settingsSchema),
    defaultValues: settings,
  });

  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: 'mcpServers',
  });

  const [newMcpUrl, setNewMcpUrl] = React.useState('');

  // Watch for provider changes to update the UI
  const provider = form.watch('provider');

  React.useEffect(() => {
    form.reset(settings);
  }, [settings, form]);

  const onSubmit = (data: ChatSettings) => {
    setSettings(data);
    setIsOpen(false);
  };

  const handleAddMcpServer = () => {
    if (newMcpUrl.trim()) {
      try {
        z.string().url().parse(newMcpUrl);
        append({ url: newMcpUrl });
        setNewMcpUrl('');
      } catch (error) {
        form.setError('mcpServers', { type: 'manual', message: 'Please enter a valid URL.' });
      }
    }
  };

  const apiKeyName = 
    provider === 'gemini' ? 'GEMINI_API_KEY' : 
    provider === 'groq' ? 'GROQ_API_KEY' : 
    'METACLAW_API_KEY';

  return (
    <Sheet open={isOpen} onOpenChange={setIsOpen}>
      <SheetTrigger asChild>
        <Button variant="ghost" size="icon">
          <Icons.settings className="h-4 w-4" />
          <span className="sr-only">Settings</span>
        </Button>
      </SheetTrigger>
      <SheetContent className="w-[400px] sm:w-[540px] flex flex-col">
        <SheetHeader>
          <SheetTitle>Settings</SheetTitle>
          <SheetDescription>Configure the chat agent and tools.</SheetDescription>
        </SheetHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="flex-1 overflow-y-auto space-y-6 pr-4">
            <div className="space-y-4">
              <h3 className="font-medium">API Configuration</h3>
              <div className='p-4 rounded-lg border border-yellow-500/50 bg-yellow-500/10 text-yellow-300 text-sm'>
                Your <code className='font-semibold text-yellow-200'>{apiKeyName}</code> must be set as an environment variable in a <code className='font-semibold text-yellow-200'>.env.local</code> file in the root of this project.
              </div>
            </div>

            <Separator />
            
            <div className="space-y-4">
                <h3 className="font-medium">Model Configuration</h3>
                <FormField
                  control={form.control}
                  name="provider"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Provider</FormLabel>
                      <Select
                        onValueChange={(value: 'gemini' | 'groq' | 'metaclaw') => {
                          field.onChange(value);
                          // This leverages the logic in the zustand store to reset the model
                          setSettings({ provider: value });
                        }}
                        defaultValue={field.value}
                      >
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Select a provider" />
                          </SelectTrigger>
                        </FormControl>
                         <SelectContent>
                          <SelectItem value="gemini">Google Gemini</SelectItem>
                          <SelectItem value="groq">Groq</SelectItem>
                          <SelectItem value="metaclaw">MetaClaw (Proxy)</SelectItem>
                        </SelectContent>
                      </Select>
                    </FormItem>
                  )}
                />
                <FormField
                control={form.control}
                name="model"
                render={({ field }) => (
                    <FormItem>
                    <FormLabel>Model</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value}>
                        <FormControl>
                        <SelectTrigger>
                            <SelectValue placeholder="Select a model" />
                        </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {MODEL_CONFIG[provider]?.models.map(model => (
                            <SelectItem key={model} value={model}>{model}</SelectItem>
                          ))}
                        </SelectContent>
                    </Select>
                    </FormItem>
                )}
                />

                <FormField
                    control={form.control}
                    name="temperature"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel>Temperature: {field.value}</FormLabel>
                            <FormControl>
                                <Slider
                                value={[field.value]}
                                onValueChange={(value) => field.onChange(value[0])}
                                max={1}
                                step={0.1}
                                />
                            </FormControl>
                        </FormItem>
                    )}
                />

                <FormField
                    control={form.control}
                    name="maxTokens"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel>Max Tokens: {field.value}</FormLabel>
                              <FormControl>
                                <Slider
                                value={[field.value]}
                                onValueChange={(value) => field.onChange(value[0])}
                                min={256}
                                max={8192}
                                step={256}
                                />
                            </FormControl>
                        </FormItem>
                    )}
                />
            </div>

            <Separator />

            <div className="space-y-4">
              <h3 className="font-medium">MCP Server Tools</h3>
              {fields.map((field, index) => (
                <div key={field.id} className="flex items-center gap-2">
                  <Input {...form.register(`mcpServers.${index}.url`)} className="flex-1" readOnly/>
                  <Button type="button" variant="destructive" size="icon" onClick={() => remove(index)}>
                    <Icons.trash className="h-4 w-4" />
                  </Button>
                </div>
              ))}
              <div className="flex items-start gap-2">
                  <div className='flex-1'>
                    <Input
                        value={newMcpUrl}
                        onChange={(e) => setNewMcpUrl(e.target.value)}
                        placeholder="http://mcp-server-url.com"
                        onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                                e.preventDefault();
                                handleAddMcpServer();
                            }
                        }}
                    />
                      {form.formState.errors.mcpServers && <FormMessage className='mt-2'>{form.formState.errors.mcpServers.message}</FormMessage>}
                  </div>
                <Button type="button" variant="outline" size="icon" onClick={handleAddMcpServer}>
                  <Icons.add className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </form>
          <SheetFooter>
            <Button type="submit" onClick={form.handleSubmit(onSubmit)}>Save Changes</Button>
          </SheetFooter>
        </Form>
      </SheetContent>
    </Sheet>
  );
}
