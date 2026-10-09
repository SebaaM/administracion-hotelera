import {api,ApiError} from "../api";
import type {Draft,Profile,Configuration,Decisions} from "./types";
export const profiles = () => api<Profile[]>("imports/profiles/");
export const drafts = () => api<Draft[]>("imports/drafts/");
export const getDraft = (id:number) => api<Draft>(`imports/drafts/${id}/`);
export const createProfile = (name:string) => api<Profile>("imports/profiles/","POST",{name});
export async function upload(file:File,profile_id:number) {
  const data=new FormData();data.set("file",file);data.set("profile_id",String(profile_id));
  return api<Draft>("imports/drafts/","POST",data);
}
export const save = (draft:Draft,configuration:Configuration,decisions:Decisions) => api<Draft>(`imports/drafts/${draft.id}/`,"PATCH",{expected_revision:draft.revision,configuration,decisions});
export const saveProfile = (id:number,configuration:Configuration) => api<Profile>(`imports/profiles/${id}/`,"PATCH",{configuration});
export const apply = (draft:Draft) => api<Draft>(`imports/drafts/${draft.id}/apply/`,"POST",{expected_revision:draft.revision});
export const discard = (draft:Draft) => api<Draft>(`imports/drafts/${draft.id}/discard/`,"POST",{expected_revision:draft.revision});
export async function download(id:number) {
  const response=await fetch(`/api/imports/drafts/${id}/csv/`,{credentials:"same-origin"});
  if(!response.ok)throw new ApiError("No se pudo exportar. Revisá el borrador y los permisos.",response.status);
  const url=URL.createObjectURL(await response.blob());const link=document.createElement("a");
  link.href=url;link.download=`reservas-lote-${id}.csv`;link.click();URL.revokeObjectURL(url);
}
