library(tidyverse)
info <- readLines('pubmed.all.journal.txt')

ans <- data.frame()
for (ll in info) {
    if (grepl('^----------', ll)) {
        jfull <- ''
        jabbr <- ''
    }
    if (grepl('^JournalTitle', ll))
        jfull <- sub('^JournalTitle: *', '', ll)
    if (grepl('^MedAbbr', ll))
        jabbr <- sub('^MedAbbr: *', '', ll)
    if (grepl('^ISSN.*: [^ ]{4}-[^ ]{4}$', ll)) {
        issn <- sub('^.+([^ ]{4}-[^ ]{4})$', '\\1', ll)
        ans <- rbind(ans, c(issn, jfull, jabbr))
    }
}

names(ans) <- c('issn', 'jfull', 'jabbr')
head(ans)

jtifs <- read_csv('IF2021.csv') %>%
    rename(issn=ISSN, impact=IF) %>%
    select(issn, impact)

left_join(ans %>% as_tibble, jtifs, by='issn') %>%
    write.csv('pubmed.journals.csv', row.names=F)
