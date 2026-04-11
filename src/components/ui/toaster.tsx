"use client"

import { useToast } from "@/hooks/use-toast"
import {
  Toast,
  ToastClose,
  ToastDescription,
  ToastProvider,
  ToastTitle,
  ToastViewport,
} from "@/components/ui/toast"
import { cn } from "@/lib/utils"

export function Toaster() {
  const { toasts } = useToast()

  return (
    <ToastProvider>
      {toasts.map(function ({ id, title, description, action, variant, ...props }) {
        const isError = variant === "destructive" || (title && title.toLowerCase().includes("error"));
        
        return (
          <Toast 
            key={id} 
            {...props} 
            className={cn(
              "ethereal-toast", 
              isError ? "ethereal-toast-error" : "ethereal-toast-success"
            )}
          >
            <div className="flex gap-4">
              <div className={cn(
                "w-10 h-10 rounded-xl flex items-center justify-center shrink-0 border",
                isError ? "bg-error/10 text-error border-error/20" : "bg-primary/10 text-primary border-primary/20"
              )}>
                <span className="material-symbols-outlined">
                  {isError ? "error" : "check_circle"}
                </span>
              </div>
              <div className="grid gap-1">
                {title && <ToastTitle className="text-sm font-bold font-headline tracking-tight">{title}</ToastTitle>}
                {description && (
                  <ToastDescription className="text-xs text-on-surface-variant font-medium leading-relaxed opacity-80">
                    {description}
                  </ToastDescription>
                )}
              </div>
            </div>
            {action}
            <ToastClose className="text-on-surface-variant/40 hover:text-on-surface" />
          </Toast>
        )
      })}
      <ToastViewport />
    </ToastProvider>
  )
}
