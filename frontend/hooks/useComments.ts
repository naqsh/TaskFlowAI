 "use client";

 import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

 import { createComment, deleteComment, fetchComments, updateComment, type Comment } from "@/lib/comments";

 const EMPTY_UUID = "00000000-0000-0000-0000-000000000000";

 export function useComments(taskId: string, currentUserId?: string | null) {
   const queryClient = useQueryClient();

   const list = useQuery({
     queryKey: ["comments", taskId],
     queryFn: () => fetchComments(taskId),
     enabled: Boolean(taskId),
   });

   const create = useMutation({
     mutationFn: (body: string) => createComment(taskId, body),
     onMutate: async (body: string) => {
       await queryClient.cancelQueries({ queryKey: ["comments", taskId] });
       const previous = queryClient.getQueryData<Comment[]>(["comments", taskId]) ?? [];

       const tempId = crypto.randomUUID();
       const optimistic: Comment = {
         id: tempId,
         workspace_id: EMPTY_UUID,
         task_id: taskId,
         author_id: currentUserId ?? null,
         body,
         created_at: new Date().toISOString(),
         updated_at: new Date().toISOString(),
       };

       queryClient.setQueryData<Comment[]>(["comments", taskId], [
         ...previous,
         optimistic,
       ]);

       return { previous, tempId };
     },
     onError: (_err, _body, ctx) => {
       if (!ctx) return;
       queryClient.setQueryData<Comment[]>(["comments", taskId], ctx.previous);
     },
     onSuccess: (serverComment, _body, ctx) => {
       if (!ctx) return;
       queryClient.setQueryData<Comment[]>(["comments", taskId], (prev) => {
         const list = prev ?? [];
         return list.map((c) => (c.id === ctx.tempId ? serverComment : c));
       });
     },
   });

   const update = useMutation({
     mutationFn: (input: { commentId: string; body: string }) =>
       updateComment(input.commentId, input.body),
     onMutate: async ({ commentId, body }) => {
       await queryClient.cancelQueries({ queryKey: ["comments", taskId] });
       const previous = queryClient.getQueryData<Comment[]>(["comments", taskId]) ?? [];
       queryClient.setQueryData<Comment[]>(["comments", taskId], (prev) => {
         const list = prev ?? [];
         return list.map((c) => (c.id === commentId ? { ...c, body } : c));
       });
       return { previous };
     },
     onError: (_err, _vars, ctx) => {
       if (!ctx) return;
       queryClient.setQueryData<Comment[]>(["comments", taskId], ctx.previous);
     },
     onSuccess: (serverComment) => {
       queryClient.setQueryData<Comment[]>(["comments", taskId], (prev) => {
         const list = prev ?? [];
         return list.map((c) => (c.id === serverComment.id ? serverComment : c));
       });
     },
   });

   const remove = useMutation({
     mutationFn: (commentId: string) => deleteComment(commentId),
     onMutate: async (commentId: string) => {
       await queryClient.cancelQueries({ queryKey: ["comments", taskId] });
       const previous = queryClient.getQueryData<Comment[]>(["comments", taskId]) ?? [];
       queryClient.setQueryData<Comment[]>(["comments", taskId], (prev) =>
         (prev ?? []).filter((c) => c.id !== commentId),
       );
       return { previous };
     },
     onError: (_err, _commentId, ctx) => {
       if (!ctx) return;
       queryClient.setQueryData<Comment[]>(["comments", taskId], ctx.previous);
     },
     onSuccess: () => {
       queryClient.invalidateQueries({ queryKey: ["comments", taskId] });
     },
   });

   return {
     comments: list.data ?? [],
     isLoading: list.isLoading,
     error: list.error,
     create,
     update,
     remove,
   };
 }

