#!/usr/bin/Rscript

##
# Music Player Magic -- a little bit of statistik. 
##

void <- Sys.setlocale("LC_TIME", "C") # just in case

IP <- "localhost"
#IP <- "192.168.12.3"

# e.g. /tmp/mpm_balken.png
PREFIX="/var/www/img/mpm/"

# Barplot (T) oder Stacked Area (F)?
BARS <- F
# gradient 'plasma' from viridis. First color is dark grey ("blackklist")
COLORS <- c("#333333", "#0D0887", "#4C02A1", "#7E03A8", "#AA2395", "#CC4778", "#E66C5C", "#F89540", "#FDC527", "#F0F921")
BACKGROUND <- "#222222"
FOREGROUND <- "#AFAFAF"
PLOTCOLOR <- "#777777"

########################################################################

# Listen holen.
rawtrx <- system("/home/hippie/mpd/musicplayermagic/lsalltimes.py", intern=T)
tracks <- as.numeric(sub(".*\t", "", rawtrx))
names(tracks) <- sub("\t.*", "", rawtrx)

toplay <- system(paste("echo pool apl | nc ",IP," 55443",sep=""),intern=T)
played <- system(paste("echo history apl | nc ",IP," 55443",sep=""),intern=T)
played <- played[nchar(played)>1]

blacklist <- setdiff(names(tracks),c(toplay,sub(".*\t","",played)))

trx <- data.frame(stringsAsFactors=F,
    row.names = names(tracks),
    cat = gsub("/.*|^Ganz","",names(tracks)),
    len = tracks
)
trx[blacklist,"cat"] <- "blacklist"
# blacklist first.
cats <- c("blacklist", setdiff(sort(unique(trx[,"cat"])), "blacklist"))

# Chart-Colors
if (length(COLORS) >= length(cats)) {
    colrs <- COLORS[1:length(cats)]
} else {
    colrs <- c(COLORS[1], colorRampPalette(COLORS[-1])(length(cats)-1))
}
names(colrs) <- cats

hrtime <- function (ds) {
    d <- ds %/% 86400
    h <- (ds %% 86400) %/% 3600
    m <- (ds %% 3600) %/% 60
    s <- ds %% 60
    return(sprintf("%d days, %#2d:%02d:%02d", d,h,m,s))
}



###======================================###
###    Gesamte Sammlung Visualisieren    ###
###======================================###

png(sprintf("%sbalken.png", PREFIX), width=900, height=600, res=110, bg="transparent", type="cairo")
    par(mfrow   = c(3,1),
        mar     = c(5, 1, 4, 1.5),
        bg      = BACKGROUND,
        fg      = PLOTCOLOR,
        col     = FOREGROUND,
        col.axis= FOREGROUND,
        col.lab = FOREGROUND,
        col.main= COLORS[8],
        col.sub = COLORS[7]
    )
    
    # 1. bar: By number of tracks
    bar1 <- c(
        length(blacklist),
        table(trx[sub(".*\t","",played), "cat"])[cats[-1]],
        table(trx[toplay, "cat"])[cats[-1]]
    )
    names(bar1)[1] <- "Blacklist"
    names(bar1)[-1] <- paste(rep(c("Added", "Remain"),each=length(cats)-1), rep(cats[-1], 2))
    bar1[is.na(bar1)] <- 0
    barplot(
        as.matrix(bar1),
        xlim=c(0, ceiling(nrow(trx) / 10000)*10000),
        col=c(colrs[1], rep(colrs[-1], 2)),
        horiz=T,
        border=NA,
        xlab="n",
        main="Number of Tracks")
    vec <- c(0, bar1[1], sum(bar1[grep("Added", names(bar1))]) + bar1[1], sum(bar1))
    names(vec) <- c("", sprintf(c("Blacklist\n%d", "Added\n%d", "Remaining\n%d"), vec[-1] - vec[-length(vec)]))
    axis(3, at=vec, labels=names(vec), hadj=1)

    bar2 <- c(
        sum(trx[blacklist,"len"]),
        sapply(cats[-1], function(cc) sum(trx[(trx[,"cat"]==cc & rownames(trx) %in% sub(".*\t","",played)),  "len"])),
        sapply(cats[-1], function(cc) sum(trx[(trx[,"cat"]==cc & rownames(trx) %in% toplay),  "len"]))
    )
    names(bar2)[1] <- "Blacklist"
    names(bar2)[-1] <- paste(rep(c("Added", "Remain"), each=length(cats[-1])), rep(cats[-1], 2))
    barplot(
        as.matrix(bar2/86400), 
        xlim=c(0, ceiling(sum(bar2) / 86400)),
        col=c(colrs[1], rep(colrs[-1], 2)),
        horiz=T,
        border=NA,
        xlab="Days",
        main="Time")
    vec <- c(0, bar2[1]/86400, (sum(bar2[grep("Added", names(bar2))]) + bar2[1])/86400, sum(bar2)/86400)
    names(vec) <- c("", sprintf(c("Blacklist\n%s", "Added\n%s", "Remaining\n%s"), hrtime(vec[-1]*86400 - vec[-length(vec)]*86400)))
    axis(3, at=vec, labels=names(vec), hadj=1)
    
    par(family="mono", font=2, mar=c(0,0,0,0))
    plot.new()
    # facts and numbers
    lgnd <- c(
        "              │               Total               │               Added               │            Remaining             ",
        "──────────────┼───────────────────────────────────┼───────────────────────────────────┼──────────────────────────────────",
        blacklist=sprintf("Blacklist     │ %#5d files  %20s │%35s│", bar1[1], hrtime(bar2[1]), ""),
        sapply(cats[-1], function(xx) {
            b1 <- bar1[grep(xx,names(bar1), fix=T)]
            b2 <- bar2[grep(xx,names(bar2), fix=T)]
            sprintf("%-13s │ %#5d files  %20s │ %#5d files  %20s │ %#5d files  %20s", 
                xx, sum(b1), hrtime(sum(b2)), b1[1], hrtime(b2[1]), b1[2], hrtime(b2[2]))
        }),
        "──────────────┼───────────────────────────────────┼───────────────────────────────────┼──────────────────────────────────",
        sprintf("%-13s │ %#5d files  %20s │ %#5d files  %20s │ %#5d files  %20s", 
                "Total", sum(bar1), hrtime(sum(bar2)), 
                sum(bar1[grep("Added ", names(bar1))]), hrtime(sum(bar2[grep("Added ", names(bar2))])),
                sum(bar1[grep("Remain ", names(bar1))]), hrtime(sum(bar2[grep("Remain ", names(bar2))]))
        )

    )
    #legend("center", lty=1, lwd=10, col=colrs[names(lgnd)], legend=lgnd)
    legend("center", pch=15, pt.cex=2, col=colrs[names(lgnd)], legend=lgnd)
void <- dev.off()

png(sprintf("%storten.png",PREFIX), width=900, height=600, res=120, bg="transparent", type="cairo")
    par(mar     = c(1,.3,4,.3),
        mfrow   = c(2, 2),
        bg      = BACKGROUND,
        fg      = PLOTCOLOR,
        col     = FOREGROUND,
        col.axis= FOREGROUND,
        col.lab = FOREGROUND,
        col.main= COLORS[8],
        col.sub = COLORS[7]
    )

    fig <- c(length(blacklist), length(played), length(toplay))
    swin <- (fig[1] / sum(fig)) * 180 + 91
    names(fig) <- paste(c("Blacklist","Added", "Remaining"), "\n(", fig, ")", sep="")
    pie(fig, col=colrs, clockwise=T, radius=1, cex=0.8, init.angle=swin, main="Number of Tracks in Shuffle")

    fig <- c(sum(trx[blacklist,"len"], na.rm=T), sum(trx[sub(".*\t","",played),"len"], na.rm=T), sum(trx[toplay,"len"], na.rm=T))
    swin <- (fig[1] / sum(fig)) * 180 + 91
    names(fig) <- paste(c("Blacklist", "Added", "Remaining"), "\n(", hrtime(fig), ")", sep="")
    pie(fig, col=colrs, clockwise=T, radius=1, cex=0.8, init.angle=swin, main="Time of Tracks in Shuffle")

    fig <- table(trx[, "cat"])[cats]
    swin <- (fig["blacklist"] / sum(fig)) * 180 + 90
    names(fig) <- paste(names(fig), " (", fig, ")", sep="")
    pie(fig, col=colrs[sub(" .*","",names(fig))], clockwise=T, radius=1, cex=0.75, init.angle=swin, main="Number of Tracks by Folder")

    fig <- sapply(cats, function(cc) sum(trx[trx[,"cat"]==cc,"len"], na.rm=T))
    swin <- (fig["blacklist"] / sum(fig)) * 180 + 90
    names(fig) <- paste(names(fig), " (", hrtime(fig), ")", sep="")
    pie(fig, col=colrs[sub(" .*","",names(fig))], clockwise=T, radius=.8, cex=0.75, init.angle=swin, main="Time of Tracks by Folder")
void <- dev.off()


###======================================###
###          Pro-Tag-Verbrauch           ###
###======================================###

# dataframe aus played
rexi <- "(.+) [0-9]{2}:[0-9]{2}:[0-9]{2}\t(.*)"
S2 <- sub(rexi, "\\2", played)
S1 <- sub(rexi, "\\1", played)
tbd <- data.frame(
    date=factor(S1, levels=unique(S1)),
    len=trx[S2,"len"],
    cat=trx[S2,"cat"]
)

# Jetzt Tabelle, Kategorie (pro Track/pro Zeit) pro Tag. Es können 
# zwischendurch Tage fehlen, z.B. weil der Shuffle nichts zu tun hatte,
# weil die Playlist noch arschlang war- Oder so.
tbd_n   <- sapply(cats[-1], function(x) table(tbd[tbd[,"cat"] == x,"date"]))
tbd_len <- sapply(cats[-1], function(x) {
    sapply(levels(tbd[,"date"]), function(y) {
        sum(tbd[tbd[,"cat"] == x & tbd[,"date"] == y,"len"], na.rm=T)
    })
})

dgbars <- function(dataset, ylab="", main="") {
    barplot(
        t(dataset), 
        ylab=ylab, 
        col=colrs[-1], 
        las=2, 
        space=0, 
        border=NA, 
        main=main
    )
    return (1:nrow(dataset))
}

dgsmooth <- function(dataset, ylab="", main="") {
    sresolution <- 20
    barwidth <- 0.3
    rbw <- round(sresolution*barwidth)

    # prepare plot-area
    plot(0, 
        ylim=c(0,max(apply(dataset,1,sum))),
        xlim=c(1,nrow(dataset)*sresolution),
        main=main, ylab=ylab, xlab="",
        frame.plot=F,
        type="n", xaxt="n"
    )
    daysx <- (1:nrow(dataset)-1)*sresolution + sresolution*barwidth/2
    axis(1, at=daysx, labels=rownames(dataset), las=2)
    
    for (ccol in ncol(dataset):1) {
        # calculate splines...
        x <- unlist(lapply(1:nrow(dataset)*sresolution, function(x) c(x-sresolution+1, x-sresolution+rbw)))
        y <- rep(apply(dataset[,1:ccol,drop=F],1,sum), each=2)
        spl <- do.call(rbind, lapply(1:(length(x)/2), function(i) {
            as.data.frame(spline(x[(i*2-1):(i*2+2)], y[(i*2-1):(i*2+2)], method="hyman", n=sresolution + barwidth * sresolution))
        }))
        # ... and draw
        polygon(rbind(c(1,0), unique(spl), c(max(x),0)), col=colrs[colnames(dataset)[ccol]], border=NA)
    }
    return(daysx)
}

daygraph <- function(dataset, ylab="", main="") {
    par(mar     = c(9, 4, 3, 1),
        bg      = BACKGROUND,
        fg      = PLOTCOLOR,
        col     = FOREGROUND,
        col.axis= FOREGROUND,
        col.lab = FOREGROUND,
        col.main= COLORS[8],
        col.sub = COLORS[7]
    )
    
    #xres <- dgbars(dataset, ylab, main)
    xres <- dgsmooth(dataset, ylab, main)
    
    hlin <- ceiling(max(apply(dataset,1,sum)))
    mult <- 1
    while (hlin > 50) {
        hlin <- hlin / 10
        mult <- mult * 10
    }
    abline(h=1:hlin*mult, lty=2, col="#ffffff17")
    abline(v=xres, lty=2, col="#ffffff17")
    #legend("right", pch=15, pt.cex=2, col=colrs[-1], legend=colnames(tbd_n))
}



# 4. Visu. ERstmal nur Barplot. Später vielleicht barplot-spline.
png(sprintf("%sbydate_n.png",PREFIX), width=900, height=600, res=72, bg="transparent", type="cairo")
daygraph(tbd_n, main="Number of Tracks per Day")
void <- dev.off()

png(sprintf("%sbydate_len.png",PREFIX), width=900, height=600, res=72, bg="transparent", type="cairo")
daygraph(tbd_len/3600, ylab="Hours", main="Time of Tracks per Day")
void <- dev.off()

# und diese 4 Bilder kommen jetzt auf eine HTML-Seite untereinander... 
