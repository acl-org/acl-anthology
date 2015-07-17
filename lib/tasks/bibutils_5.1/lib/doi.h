/*
 * doi.h
 *
 * Copyright (c) Chris Putnam 2004-2013
 *
 * Source code released under the GPL version 2
 *
 */
#ifndef DOI_H
#define DOI_H

#include "newstr.h"
#include "fields.h"

extern void doi_to_url( fields *info, int n, char *urltag, newstr *doi_url );
extern int is_doi( char *s );
extern void pmid_to_url( fields *info, int n, char *urltag, newstr *pmid_url );
extern void arxiv_to_url( fields *info, int n, char *urltag, newstr *arxiv_url );
extern void jstor_to_url( fields *info, int n, char *urltag, newstr *jstor_url );

#endif
